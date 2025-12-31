import asyncio
import logging
import sys

from gmail_monitor import GmailMonitor, GmailAPIError
from telegram_bot import TelegramNotifier
import config

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    datefmt='%H:%M:%S'
)
logger = logging.getLogger(__name__)


def validate_config() -> None:
    """Проверка конфигурации при запуске."""
    errors: list[str] = []

    if not getattr(config, 'TELEGRAM_BOT_TOKEN', None):
        errors.append("TELEGRAM_BOT_TOKEN не задан")

    if not getattr(config, 'ALLOWED_USER_IDS', None):
        errors.append("ALLOWED_USER_IDS пустой или не задан")

    if not getattr(config, 'GMAIL_CREDENTIALS_FILE', None):
        errors.append("GMAIL_CREDENTIALS_FILE не задан")

    if errors:
        logger.error("Ошибки конфигурации:")
        for err in errors:
            logger.error(f"  - {err}")
        sys.exit(1)

    logger.info("Конфигурация проверена ✓")


async def main() -> None:
    logger.info("=" * 40)
    logger.info("Claude Auth Code Bot")
    logger.info("=" * 40)

    validate_config()

    gmail = GmailMonitor()
    telegram = TelegramNotifier()

    logger.info("Авторизация в Gmail...")
    gmail.authenticate()

    logger.info("Отправка стартового сообщения в Telegram...")
    await telegram.send_startup_message()

    logger.info(f"Мониторинг почты (интервал: {config.CHECK_INTERVAL} сек). Ctrl+C для остановки")

    while True:
        try:
            emails = gmail.get_unread_claude_emails()

            if emails:
                logger.info(f"Найдено {len(emails)} новых писем")

                for email in emails:
                    sent = await telegram.send_code(email)
                    if sent:
                        gmail.mark_as_read(email['id'])
                    else:
                        logger.warning("Telegram не отправлен, письмо НЕ помечено прочитанным")
            else:
                logger.debug("Новых писем нет")

            await asyncio.sleep(config.CHECK_INTERVAL)

        except GmailAPIError as e:
            logger.error(f"Gmail API ошибка: {e}")
            logger.info("Повтор через 30 сек...")
            await asyncio.sleep(30)

        except Exception as e:
            logger.exception(f"Неожиданная ошибка: {e}")
            await asyncio.sleep(30)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Бот остановлен")
        sys.exit(0)
