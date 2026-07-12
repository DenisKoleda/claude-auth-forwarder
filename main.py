import asyncio
import logging
import sys

import settings
from admin_state import AdminState
from gmail_monitor import GmailAPIError, GmailMonitor, TokenExpiredError
from i18n import set_language, t
from state_store import StateStore
from status_monitor import OpenAIStatusMonitor, StatusAPIError
from telegram_admin import TelegramAdmin
from telegram_bot import TelegramNotifier

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)
logging.getLogger("httpx").setLevel(logging.WARNING)


def validate_config() -> None:
    errors: list[str] = []
    if not settings.TELEGRAM_BOT_TOKEN:
        errors.append(t("config_error_token"))
    if not settings.ALLOWED_USER_IDS:
        errors.append(t("config_error_users"))
    if not settings.GMAIL_CREDENTIALS_FILE:
        errors.append(t("config_error_gmail"))
    if (
        settings.ENABLE_CLAUDE_EMAILS or settings.ENABLE_OPENAI_EMAILS
    ) and not settings.AUTH_RECIPIENT_IDS:
        errors.append("AUTH_RECIPIENT_IDS is empty")
    if settings.ENABLE_BILLING_EMAILS and not settings.BILLING_RECIPIENT_IDS:
        errors.append("BILLING_RECIPIENT_IDS is empty")
    if settings.ENABLE_OPENAI_INCIDENTS and not settings.INCIDENT_RECIPIENT_IDS:
        errors.append("INCIDENT_RECIPIENT_IDS is empty")
    if not settings.ADMIN_USER_IDS:
        errors.append("ADMIN_USER_IDS is empty")
    if errors:
        raise RuntimeError("; ".join(errors))


async def gmail_loop(gmail: GmailMonitor, telegram: TelegramNotifier, store: StateStore) -> None:
    backoff = 30
    while True:
        store.touch_health("heartbeat", "gmail_loop")
        try:
            emails = await asyncio.to_thread(gmail.get_unread_emails)
            store.touch_health("gmail", f"messages={len(emails)}")
            backoff = 30
            if emails:
                logger.info(t("emails_found", count=len(emails)))
            for email in emails:
                if email.get("stale"):
                    logger.warning("Skipping stale %s email %s", email.get("kind"), email["id"])
                    await asyncio.to_thread(gmail.mark_as_read, email["id"])
                    continue
                if await telegram.deliver_email(email):
                    await asyncio.to_thread(gmail.mark_as_read, email["id"])
                else:
                    logger.warning(t("telegram_not_sent"))
            await asyncio.sleep(settings.CHECK_INTERVAL)
        except TokenExpiredError as exc:
            logger.error(str(exc))
            await telegram.send_token_expired_message()
            store.touch_health("gmail", "reauthentication required")
            await asyncio.to_thread(gmail.authenticate)
        except GmailAPIError as exc:
            logger.error(t("gmail_api_error", error=exc))
            await asyncio.sleep(backoff)
            backoff = min(backoff * 2, 300)
        except Exception as exc:
            logger.exception(t("unexpected_error", error=exc))
            await asyncio.sleep(backoff)
            backoff = min(backoff * 2, 300)


async def status_loop(monitor: OpenAIStatusMonitor, store: StateStore) -> None:
    backoff = settings.STATUS_CHECK_INTERVAL
    while True:
        store.touch_health("heartbeat", "status_loop")
        try:
            await monitor.sync()
            backoff = settings.STATUS_CHECK_INTERVAL
            await asyncio.sleep(settings.STATUS_CHECK_INTERVAL)
        except StatusAPIError as exc:
            logger.error(str(exc))
            await asyncio.sleep(backoff)
            backoff = min(backoff * 2, 600)
        except Exception as exc:
            logger.exception("Unexpected status monitor error: %s", exc)
            await asyncio.sleep(backoff)
            backoff = min(backoff * 2, 600)


async def heartbeat_loop(store: StateStore) -> None:
    while True:
        store.touch_health("heartbeat", "main")
        await asyncio.sleep(15)


async def main() -> None:
    set_language(settings.LANGUAGE)
    validate_config()

    store = StateStore(settings.STATE_DB_FILE)
    admin_state = AdminState()
    telegram = TelegramNotifier(store)
    admin = TelegramAdmin(admin_state, store)
    gmail = GmailMonitor(admin_state)
    status = OpenAIStatusMonitor(admin_state, store, telegram)

    admin_started = False
    try:
        try:
            await admin.start()
            admin_started = True
        except Exception as exc:
            logger.exception("Telegram admin failed to start, continuing: %s", exc)

        await telegram.send_startup_message()
        logger.info(t("gmail_auth_start"))
        await asyncio.to_thread(gmail.authenticate)
        store.touch_health("gmail", "authenticated")
        store.touch_health("openai_status", "starting")

        async with asyncio.TaskGroup() as tasks:
            tasks.create_task(gmail_loop(gmail, telegram, store))
            tasks.create_task(status_loop(status, store))
            tasks.create_task(heartbeat_loop(store))
    finally:
        if admin_started:
            await admin.stop()
        store.close()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info(t("bot_stopped"))
        sys.exit(0)
