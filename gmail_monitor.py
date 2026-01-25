import base64
import logging
import os
import re
from typing import Any

from google.auth.exceptions import RefreshError
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

import config
from i18n import t

logger = logging.getLogger(__name__)


def _can_open_browser() -> bool:
    """Check if browser can be opened."""
    try:
        # Check for DISPLAY (Linux) or if not in SSH
        if os.environ.get("SSH_CONNECTION") or os.environ.get("SSH_CLIENT"):
            return False
        if (
            os.name == "posix"
            and not os.environ.get("DISPLAY")
            and not os.environ.get("WAYLAND_DISPLAY")
        ):
            # macOS can always open browser, Linux without DISPLAY cannot
            import platform

            if platform.system() != "Darwin":
                return False
        return True
    except Exception:
        return False


class GmailAPIError(Exception):
    """Error when working with Gmail API."""

    pass


class GmailMonitor:
    def __init__(self) -> None:
        self.service: Any = None
        self.creds: Credentials | None = None

    def authenticate(self) -> None:
        """Authenticate with Gmail API."""
        if os.path.exists(config.GMAIL_TOKEN_FILE):
            self.creds = Credentials.from_authorized_user_file(
                config.GMAIL_TOKEN_FILE, config.GMAIL_SCOPES
            )

        if not self.creds or not self.creds.valid:
            if self.creds and self.creds.expired and self.creds.refresh_token:
                try:
                    self.creds.refresh(Request())
                except RefreshError as e:
                    # Token revoked or expired - need full re-auth
                    logger.warning(t("token_refresh_failed", error=e))
                    if os.path.exists(config.GMAIL_TOKEN_FILE):
                        os.remove(config.GMAIL_TOKEN_FILE)
                        logger.info(t("token_removed"))
                    self.creds = None

            if not self.creds or not self.creds.valid:
                flow = InstalledAppFlow.from_client_secrets_file(
                    config.GMAIL_CREDENTIALS_FILE, config.GMAIL_SCOPES
                )
                # Auto-detect: use console auth if browser unavailable (VPS/SSH)
                if _can_open_browser():
                    self.creds = flow.run_local_server(port=0, open_browser=True)
                else:
                    logger.info(t("console_auth_info"))
                    self.creds = flow.run_console()

            with open(config.GMAIL_TOKEN_FILE, "w") as token:
                token.write(self.creds.to_json())

        self.service = build("gmail", "v1", credentials=self.creds, cache_discovery=False)
        logger.info(t("gmail_auth_success"))

    def _is_token_error(self, error: Exception) -> bool:
        """Check if error is related to expired/revoked token."""
        error_str = str(error).lower()
        return "invalid_grant" in error_str or "token" in error_str and (
            "expired" in error_str or "revoked" in error_str
        )

    def _reauth_if_token_error(self, error: Exception) -> bool:
        """Re-authenticate if error is token-related. Returns True if re-auth happened."""
        if self._is_token_error(error):
            logger.warning(t("token_expired_reauth"))
            if os.path.exists(config.GMAIL_TOKEN_FILE):
                os.remove(config.GMAIL_TOKEN_FILE)
            self.creds = None
            self.authenticate()
            return True
        return False

    def get_unread_claude_emails(self, _retry: bool = True) -> list[dict[str, Any]]:
        """Get unread emails from Claude/Anthropic.

        Returns:
            list: List of emails (empty if no new ones)

        Raises:
            GmailAPIError: On API error
        """
        try:
            results = (
                self.service.users()
                .messages()
                .list(userId="me", q=config.GMAIL_QUERY, maxResults=10)
                .execute()
            )

            messages = results.get("messages", [])
            emails = []

            for msg in messages:
                email_data = self._get_email_content(msg["id"])
                if email_data:
                    emails.append(email_data)

            return emails
        except Exception as e:
            # If token expired during API call, re-auth and retry once
            if _retry and self._reauth_if_token_error(e):
                return self.get_unread_claude_emails(_retry=False)
            raise GmailAPIError(t("gmail_fetch_error", error=e)) from e

    def _get_email_content(self, msg_id: str) -> dict[str, Any] | None:
        """Get email content."""
        try:
            message = (
                self.service.users().messages().get(userId="me", id=msg_id, format="full").execute()
            )

            headers = message["payload"]["headers"]
            subject = self._get_header(headers, "subject", t("no_subject"))
            sender = self._get_header(headers, "from", t("unknown_sender"))

            body = self._extract_body(message["payload"])
            auth_data = self._extract_auth_data(body)

            return {
                "id": msg_id,
                "subject": subject,
                "from": sender,
                "body": body,
                "auth_data": auth_data,
            }
        except Exception as e:
            logger.error(t("email_read_error", msg_id=msg_id, error=e))
            return None

    def _get_header(self, headers: list[dict], name: str, default: str = "") -> str:
        """Extract header value by name."""
        return next((h["value"] for h in headers if h["name"].lower() == name.lower()), default)

    def _decode_body_data(self, data: str) -> str:
        """Decode base64 email body data."""
        return base64.urlsafe_b64decode(data).decode("utf-8")

    def _extract_body(self, payload: dict) -> str:
        """Extract email text."""
        if payload.get("body", {}).get("data"):
            return self._decode_body_data(payload["body"]["data"])

        if "parts" not in payload:
            return ""

        html_body = ""
        for part in payload["parts"]:
            data = part.get("body", {}).get("data")
            if not data:
                continue
            if part["mimeType"] == "text/plain":
                return self._decode_body_data(data)
            if part["mimeType"] == "text/html":
                html_body = self._decode_body_data(data)

        return html_body

    def _extract_auth_data(self, body: str) -> dict[str, str] | None:
        """Extract auth link or code from email body."""
        # Patterns for auth data: (type, regex, group)
        patterns = [
            # Desktop link: magic-link#token
            ("link", r'https://claude\.ai/magic-link#[^\s"<>]+', 0),
            # Mobile link: magic-link?client=ios#token (or other clients)
            ("mobile_link", r'https://claude\.ai/magic-link\?client=[^#]+#[^\s"<>]+', 0),
            ("code", r"(?:code|код|verification|pin)[:\s]+(\d{4,8})", 1),
            ("code", r"\b(\d{6})\b", 1),
        ]

        for auth_type, pattern, group in patterns:
            match = re.search(pattern, body, re.IGNORECASE)
            if match:
                return {"type": auth_type, "value": match.group(group)}

        return None

    def mark_as_read(self, msg_id: str, _retry: bool = True) -> None:
        """Mark email as read."""
        try:
            self.service.users().messages().modify(
                userId="me", id=msg_id, body={"removeLabelIds": ["UNREAD"]}
            ).execute()
            logger.info(t("email_marked_read", msg_id=msg_id))
        except Exception as e:
            # If token expired during API call, re-auth and retry once
            if _retry and self._reauth_if_token_error(e):
                return self.mark_as_read(msg_id, _retry=False)
            logger.error(t("email_mark_error", error=e))
