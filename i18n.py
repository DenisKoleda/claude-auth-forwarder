"""Internationalization module for the bot.

Supports English (en) and Russian (ru) languages.
"""

from typing import Any

# All messages in both languages
MESSAGES: dict[str, dict[str, str]] = {
    # ===== main.py =====
    "config_error_token": {
        "en": "TELEGRAM_BOT_TOKEN is not set",
        "ru": "TELEGRAM_BOT_TOKEN не задан",
    },
    "config_error_users": {
        "en": "ALLOWED_USER_IDS is empty or not set",
        "ru": "ALLOWED_USER_IDS пустой или не задан",
    },
    "config_error_gmail": {
        "en": "GMAIL_CREDENTIALS_FILE is not set",
        "ru": "GMAIL_CREDENTIALS_FILE не задан",
    },
    "config_errors_header": {
        "en": "Configuration errors:",
        "ru": "Ошибки конфигурации:",
    },
    "config_ok": {
        "en": "Configuration verified ✓",
        "ru": "Конфигурация проверена ✓",
    },
    "gmail_auth_start": {
        "en": "Authenticating with Gmail...",
        "ru": "Авторизация в Gmail...",
    },
    "telegram_startup": {
        "en": "Sending startup message to Telegram...",
        "ru": "Отправка стартового сообщения в Telegram...",
    },
    "monitoring_start": {
        "en": "Monitoring email (interval: {interval} sec). Ctrl+C to stop",
        "ru": "Мониторинг почты (интервал: {interval} сек). Ctrl+C для остановки",
    },
    "emails_found": {
        "en": "Found {count} new email(s)",
        "ru": "Найдено {count} новых писем",
    },
    "telegram_not_sent": {
        "en": "Telegram not sent, email NOT marked as read",
        "ru": "Telegram не отправлен, письмо НЕ помечено прочитанным",
    },
    "no_new_emails": {
        "en": "No new emails",
        "ru": "Новых писем нет",
    },
    "gmail_api_error": {
        "en": "Gmail API error: {error}",
        "ru": "Gmail API ошибка: {error}",
    },
    "retry_in_30": {
        "en": "Retrying in 30 sec...",
        "ru": "Повтор через 30 сек...",
    },
    "unexpected_error": {
        "en": "Unexpected error: {error}",
        "ru": "Неожиданная ошибка: {error}",
    },
    "bot_stopped": {
        "en": "Bot stopped",
        "ru": "Бот остановлен",
    },
    # ===== telegram_bot.py =====
    "msg_sent_to_user": {
        "en": "Message sent to user {user_id}",
        "ru": "Сообщение отправлено пользователю {user_id}",
    },
    "msg_send_error": {
        "en": "Error sending to user {user_id}: {error}",
        "ru": "Ошибка отправки пользователю {user_id}: {error}",
    },
    "auth_link_header": {
        "en": "🔐 Claude login link",
        "ru": "🔐 Ссылка для входа в Claude",
    },
    "auth_mobile_link_header": {
        "en": "📱 Claude mobile login link",
        "ru": "📱 Ссылка для входа в Claude (мобильный)",
    },
    "auth_code_header": {
        "en": "🔐 Claude authorization code",
        "ru": "🔐 Код авторизации Claude",
    },
    "time_label": {
        "en": "Time",
        "ru": "Время",
    },
    "code_label": {
        "en": "Code",
        "ru": "Код",
    },
    "new_email_header": {
        "en": "📧 New email from Claude/Anthropic",
        "ru": "📧 Новое письмо от Claude/Anthropic",
    },
    "subject_label": {
        "en": "Subject",
        "ru": "Тема",
    },
    "no_subject": {
        "en": "No subject",
        "ru": "Без темы",
    },
    "extraction_failed": {
        "en": "Could not extract code/link. Please check email manually.",
        "ru": "Не удалось извлечь код/ссылку. Проверьте почту вручную.",
    },
    "bot_started": {
        "en": "✅ Bot started!",
        "ru": "✅ Бот запущен!",
    },
    "checking_email_interval": {
        "en": "Checking email every {interval} sec.",
        "ru": "Проверяю почту каждые {interval} сек.",
    },
    "waiting_for_emails": {
        "en": "Waiting for Claude/Anthropic emails...",
        "ru": "Жду писем от Claude/Anthropic...",
    },
    # ===== gmail_monitor.py =====
    "console_auth_info": {
        "en": "Running in console mode (VPS/SSH detected). Open the URL in your browser and enter the code.",
        "ru": "Консольный режим (обнаружен VPS/SSH). Откройте URL в браузере и введите код.",
    },
    "open_auth_url": {
        "en": "Open this URL in your browser:",
        "ru": "Откройте эту ссылку в браузере:",
    },
    "enter_auth_code": {
        "en": "Enter authorization code: ",
        "ru": "Введите код авторизации: ",
    },
    "gmail_auth_success": {
        "en": "Gmail authentication successful",
        "ru": "Gmail авторизация успешна",
    },
    "gmail_fetch_error": {
        "en": "Error fetching emails: {error}",
        "ru": "Ошибка при получении писем: {error}",
    },
    "unknown_sender": {
        "en": "Unknown",
        "ru": "Неизвестный",
    },
    "email_read_error": {
        "en": "Error reading email {msg_id}: {error}",
        "ru": "Ошибка при чтении письма {msg_id}: {error}",
    },
    "email_marked_read": {
        "en": "Email {msg_id} marked as read",
        "ru": "Письмо {msg_id} помечено как прочитанное",
    },
    "email_mark_error": {
        "en": "Error marking email as read: {error}",
        "ru": "Ошибка при пометке письма: {error}",
    },
    "token_refresh_failed": {
        "en": "Token refresh failed (expired/revoked): {error}",
        "ru": "Не удалось обновить токен (истёк/отозван): {error}",
    },
    "token_removed": {
        "en": "Old token removed, re-authentication required",
        "ru": "Старый токен удалён, требуется повторная авторизация",
    },
    "token_expired_reauth": {
        "en": "Token expired during API call, re-authenticating...",
        "ru": "Токен истёк во время запроса, повторная авторизация...",
    },
    "auth_success_browser": {
        "en": "Authentication successful! You can close this window.",
        "ru": "Авторизация успешна! Можете закрыть это окно.",
    },
}

# Current language (set from config)
_current_lang: str = "ru"


def set_language(lang: str) -> None:
    """Set the current language.

    Args:
        lang: Language code ('en' or 'ru')
    """
    global _current_lang
    _current_lang = lang if lang in ("en", "ru") else "en"


def get_language() -> str:
    """Get current language code."""
    return _current_lang


def t(key: str, **kwargs: Any) -> str:
    """Get translated message.

    Args:
        key: Message key
        **kwargs: Format arguments

    Returns:
        Translated and formatted message
    """
    msg_dict = MESSAGES.get(key, {})
    msg = msg_dict.get(_current_lang, msg_dict.get("en", f"[{key}]"))
    if kwargs:
        return msg.format(**kwargs)
    return msg
