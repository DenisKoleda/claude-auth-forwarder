import base64
import logging
import os
import re
from typing import Any

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

import config

logger = logging.getLogger(__name__)


def _can_open_browser() -> bool:
    """Проверить, можно ли открыть браузер."""
    try:
        # Проверяем наличие DISPLAY (Linux) или что не в SSH
        if os.environ.get('SSH_CONNECTION') or os.environ.get('SSH_CLIENT'):
            return False
        if os.name == 'posix' and not os.environ.get('DISPLAY') and not os.environ.get('WAYLAND_DISPLAY'):
            # macOS всегда может открыть браузер, Linux без DISPLAY — нет
            import platform
            if platform.system() != 'Darwin':
                return False
        return True
    except Exception:
        return False


class GmailAPIError(Exception):
    """Ошибка при работе с Gmail API"""
    pass


class GmailMonitor:
    def __init__(self) -> None:
        self.service: Any = None
        self.creds: Credentials | None = None

    def authenticate(self) -> None:
        """Авторизация в Gmail API."""
        if os.path.exists(config.GMAIL_TOKEN_FILE):
            self.creds = Credentials.from_authorized_user_file(
                config.GMAIL_TOKEN_FILE, config.GMAIL_SCOPES
            )

        if not self.creds or not self.creds.valid:
            if self.creds and self.creds.expired and self.creds.refresh_token:
                self.creds.refresh(Request())
            else:
                flow = InstalledAppFlow.from_client_secrets_file(
                    config.GMAIL_CREDENTIALS_FILE, config.GMAIL_SCOPES
                )
                # Автоопределение: открываем браузер только если можем
                should_open_browser = _can_open_browser()
                if not should_open_browser:
                    logger.info("Браузер не будет открыт автоматически. Скопируйте URL из консоли.")
                self.creds = flow.run_local_server(port=0, open_browser=should_open_browser)

            with open(config.GMAIL_TOKEN_FILE, 'w') as token:
                token.write(self.creds.to_json())

        self.service = build('gmail', 'v1', credentials=self.creds, cache_discovery=False)
        logger.info("Gmail авторизация успешна")

    def get_unread_claude_emails(self) -> list[dict[str, Any]]:
        """Получить непрочитанные письма от Claude/Anthropic.

        Returns:
            list: Список писем (пустой если нет новых)

        Raises:
            GmailAPIError: При ошибке API
        """
        try:
            results = self.service.users().messages().list(
                userId='me',
                q=config.GMAIL_QUERY,
                maxResults=10
            ).execute()

            messages = results.get('messages', [])
            emails = []

            for msg in messages:
                email_data = self._get_email_content(msg['id'])
                if email_data:
                    emails.append(email_data)

            return emails
        except Exception as e:
            raise GmailAPIError(f"Ошибка при получении писем: {e}") from e

    def _get_email_content(self, msg_id: str) -> dict[str, Any] | None:
        """Получить содержимое письма"""
        try:
            message = self.service.users().messages().get(
                userId='me',
                id=msg_id,
                format='full'
            ).execute()

            headers = message['payload']['headers']
            subject = self._get_header(headers, 'subject', 'Без темы')
            sender = self._get_header(headers, 'from', 'Неизвестный')

            body = self._extract_body(message['payload'])
            auth_data = self._extract_auth_data(body)

            return {
                'id': msg_id,
                'subject': subject,
                'from': sender,
                'body': body,
                'auth_data': auth_data
            }
        except Exception as e:
            logger.error(f"Ошибка при чтении письма {msg_id}: {e}")
            return None

    def _get_header(self, headers: list[dict], name: str, default: str = '') -> str:
        """Извлечь значение заголовка по имени."""
        return next(
            (h['value'] for h in headers if h['name'].lower() == name.lower()),
            default
        )

    def _decode_body_data(self, data: str) -> str:
        """Декодировать base64 данные тела письма."""
        return base64.urlsafe_b64decode(data).decode('utf-8')

    def _extract_body(self, payload: dict) -> str:
        """Извлечь текст письма"""
        if payload.get('body', {}).get('data'):
            return self._decode_body_data(payload['body']['data'])

        if 'parts' not in payload:
            return ""

        html_body = ""
        for part in payload['parts']:
            data = part.get('body', {}).get('data')
            if not data:
                continue
            if part['mimeType'] == 'text/plain':
                return self._decode_body_data(data)
            if part['mimeType'] == 'text/html':
                html_body = self._decode_body_data(data)

        return html_body

    def _extract_auth_data(self, body: str) -> dict[str, str] | None:
        """Извлечь ссылку или код авторизации из текста письма"""
        # Паттерны для поиска auth данных: (тип, regex, группа)
        patterns = [
            ('link', r'https://claude\.ai/magic-link#[^\s"<>]+', 0),
            ('code', r'(?:code|код|verification|pin)[:\s]+(\d{4,8})', 1),
            ('code', r'\b(\d{6})\b', 1),
        ]

        for auth_type, pattern, group in patterns:
            match = re.search(pattern, body, re.IGNORECASE)
            if match:
                return {'type': auth_type, 'value': match.group(group)}

        return None

    def mark_as_read(self, msg_id: str) -> None:
        """Пометить письмо как прочитанное"""
        try:
            self.service.users().messages().modify(
                userId='me',
                id=msg_id,
                body={'removeLabelIds': ['UNREAD']}
            ).execute()
            logger.info(f"Письмо {msg_id} помечено как прочитанное")
        except Exception as e:
            logger.error(f"Ошибка при пометке письма: {e}")
