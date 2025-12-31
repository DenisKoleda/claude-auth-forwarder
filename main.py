import asyncio
import logging
import sys

import config
from gmail_monitor import GmailAPIError, GmailMonitor
from i18n import set_language, t
from telegram_bot import TelegramNotifier

# Setup logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s", datefmt="%H:%M:%S"
)
logger = logging.getLogger(__name__)


def validate_config() -> None:
    """Validate configuration at startup."""
    errors: list[str] = []

    if not getattr(config, "TELEGRAM_BOT_TOKEN", None):
        errors.append(t("config_error_token"))

    if not getattr(config, "ALLOWED_USER_IDS", None):
        errors.append(t("config_error_users"))

    if not getattr(config, "GMAIL_CREDENTIALS_FILE", None):
        errors.append(t("config_error_gmail"))

    if errors:
        logger.error(t("config_errors_header"))
        for err in errors:
            logger.error(f"  - {err}")
        sys.exit(1)

    logger.info(t("config_ok"))


async def main() -> None:
    # Initialize language from config
    lang = getattr(config, "LANGUAGE", "ru")
    set_language(lang)

    logger.info("=" * 40)
    logger.info("Claude Auth Code Bot")
    logger.info("=" * 40)

    validate_config()

    gmail = GmailMonitor()
    telegram = TelegramNotifier()

    logger.info(t("gmail_auth_start"))
    gmail.authenticate()

    logger.info(t("telegram_startup"))
    await telegram.send_startup_message()

    logger.info(t("monitoring_start", interval=config.CHECK_INTERVAL))

    while True:
        try:
            emails = gmail.get_unread_claude_emails()

            if emails:
                logger.info(t("emails_found", count=len(emails)))

                for email in emails:
                    sent = await telegram.send_code(email)
                    if sent:
                        gmail.mark_as_read(email["id"])
                    else:
                        logger.warning(t("telegram_not_sent"))
            else:
                logger.debug(t("no_new_emails"))

            await asyncio.sleep(config.CHECK_INTERVAL)

        except GmailAPIError as e:
            logger.error(t("gmail_api_error", error=e))
            logger.info(t("retry_in_30"))
            await asyncio.sleep(30)

        except Exception as e:
            logger.exception(t("unexpected_error", error=e))
            await asyncio.sleep(30)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info(t("bot_stopped"))
        sys.exit(0)
