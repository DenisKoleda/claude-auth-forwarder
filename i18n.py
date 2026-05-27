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
        "en": "🔐 {provider} login link",
        "ru": "🔐 Ссылка для входа в {provider}",
    },
    "auth_mobile_link_header": {
        "en": "📱 {provider} mobile login link",
        "ru": "📱 Ссылка для входа в {provider} (мобильный)",
    },
    "auth_code_header": {
        "en": "🔐 {provider} authorization code",
        "ru": "🔐 Код авторизации {provider}",
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
        "en": "📧 New email from {provider}",
        "ru": "📧 Новое письмо от {provider}",
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
    "payment_failed_header": {
        "en": "💳 Payment to {provider} failed",
        "ru": "💳 Оплата {provider} не прошла",
    },
    "payment_success_header": {
        "en": "✅ Payment to {provider} successful",
        "ru": "✅ Оплата {provider} прошла",
    },
    "subscription_paused_header": {
        "en": "⏸ {provider} subscription paused",
        "ru": "⏸ Подписка {provider} приостановлена",
    },
    "subscription_paused_body": {
        "en": "Access to paid features is paused due to a failed payment. Pay the outstanding invoice to restore access.",
        "ru": "Доступ к платным функциям приостановлен из-за неудачной оплаты. Оплатите счёт, чтобы восстановить доступ.",
    },
    "payment_amount": {
        "en": "Amount",
        "ru": "Сумма",
    },
    "unknown_amount": {
        "en": "unknown",
        "ru": "неизвестно",
    },
    "payment_card": {
        "en": "Card",
        "ru": "Карта",
    },
    "payment_plan": {
        "en": "Plan",
        "ru": "Тариф",
    },
    "payment_period": {
        "en": "Period",
        "ru": "Период",
    },
    "payment_receipt_number": {
        "en": "Receipt",
        "ru": "Чек",
    },
    "payment_action": {
        "en": "Update payment method at claude.ai/settings/billing",
        "ru": "Обновите способ оплаты: claude.ai/settings/billing",
    },
    "openai_api_funded_header": {
        "en": "✅ OpenAI API balance funded",
        "ru": "✅ Баланс OpenAI API пополнен",
    },
    "openai_usage_limits_header": {
        "en": "✅ OpenAI API usage limits increased",
        "ru": "✅ Лимиты OpenAI API увеличены",
    },
    "openai_billing_action": {
        "en": "Check billing: platform.openai.com/settings/organization/billing/overview",
        "ru": "Проверьте биллинг: platform.openai.com/settings/organization/billing/overview",
    },
    "subscription_cancel_pending_header": {
        "en": "⚠️ {provider} subscription will not renew",
        "ru": "⚠️ Подписка {provider} не будет продлена",
    },
    "subscription_started_header": {
        "en": "✅ {provider} subscription started",
        "ru": "✅ Подписка {provider} оформлена",
    },
    "openai_subscription_action": {
        "en": "Manage subscription: chatgpt.com/account/manage",
        "ru": "Управление подпиской: chatgpt.com/account/manage",
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
        "en": "Waiting for auth and billing emails...",
        "ru": "Жду письма с кодами и оплатами...",
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
    # ===== OAuth web page =====
    "auth_page_title": {
        "en": "Gmail Authorization",
        "ru": "Авторизация Gmail",
    },
    "auth_page_step1": {
        "en": "1. Click the link below to authorize Gmail access:",
        "ru": "1. Нажмите на ссылку ниже для авторизации доступа к Gmail:",
    },
    "auth_page_link": {
        "en": "Authorize Gmail",
        "ru": "Авторизовать Gmail",
    },
    "auth_page_step2": {
        "en": "2. After authorization, your browser will try to redirect to localhost and show an error — this is expected.",
        "ru": "2. После авторизации браузер попытается перейти на localhost и покажет ошибку — это нормально.",
    },
    "auth_page_step3": {
        "en": "3. Copy the full URL from the browser address bar and paste it below:",
        "ru": "3. Скопируйте полный URL из адресной строки браузера и вставьте ниже:",
    },
    "auth_page_placeholder": {
        "en": "http://localhost:8080/?state=...&code=...&scope=...",
        "ru": "http://localhost:8080/?state=...&code=...&scope=...",
    },
    "auth_page_submit": {
        "en": "Submit",
        "ru": "Отправить",
    },
    "auth_server_started": {
        "en": "OAuth web page started on port {port}",
        "ru": "Веб-страница OAuth запущена на порту {port}",
    },
    "auth_server_hint": {
        "en": "Open {url}/ in your browser to authorize Gmail",
        "ru": "Откройте {url}/ в браузере для авторизации Gmail",
    },
    "auth_code_not_found": {
        "en": "Authorization code not found in the URL. Try again.",
        "ru": "Код авторизации не найден в URL. Попробуйте ещё раз.",
    },
    # ===== Token expiry =====
    "token_fully_expired": {
        "en": "Gmail token is expired/revoked. Re-authentication required — restart the container.",
        "ru": "Токен Gmail истёк/отозван. Требуется повторная авторизация — перезапустите контейнер.",
    },
    "token_expired_tg_header": {
        "en": "⚠️ Gmail token expired!",
        "ru": "⚠️ Токен Gmail истёк!",
    },
    "token_expired_tg_body": {
        "en": "The bot cannot access Gmail. The token has been revoked or expired.",
        "ru": "Бот не может получить доступ к Gmail. Токен был отозван или истёк.",
    },
    "token_expired_tg_action": {
        "en": "Restart the container to re-authorize:\ndocker-compose restart",
        "ru": "Перезапустите контейнер для повторной авторизации:\ndocker-compose restart",
    },
    "bot_stopped_token_expired": {
        "en": "Bot stopped: Gmail token expired. Restart to re-authorize.",
        "ru": "Бот остановлен: токен Gmail истёк. Перезапустите для повторной авторизации.",
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
