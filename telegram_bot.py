import logging
from datetime import datetime
from typing import Any

from telegram import Bot
from telegram.error import TelegramError

import config
from i18n import t

logger = logging.getLogger(__name__)


class TelegramNotifier:
    def __init__(self) -> None:
        self.bot = Bot(token=config.TELEGRAM_BOT_TOKEN)

    async def _broadcast(self, message: str, log_success: bool = True) -> int:
        """Send message to all allowed users.

        Args:
            message: Message text
            log_success: Log successful sends

        Returns:
            int: Number of successful sends
        """
        success_count = 0
        for user_id in config.ALLOWED_USER_IDS:
            try:
                await self.bot.send_message(chat_id=user_id, text=message)
                if log_success:
                    logger.info(t("msg_sent_to_user", user_id=user_id))
                success_count += 1
            except TelegramError as e:
                logger.error(t("msg_send_error", user_id=user_id, error=e))
        return success_count

    def _format_auth_message(self, auth_data: dict[str, str], time_now: str) -> str:
        """Format message with auth data."""
        time_label = t("time_label")
        if auth_data["type"] == "link":
            header = t("auth_link_header")
            return f"{header}\n\n{time_label}: {time_now}\n\n{auth_data['value']}"
        if auth_data["type"] == "mobile_link":
            header = t("auth_mobile_link_header")
            return f"{header}\n\n{time_label}: {time_now}\n\n{auth_data['value']}"
        header = t("auth_code_header")
        code_label = t("code_label")
        return f"{header}\n\n{code_label}: {auth_data['value']}\n{time_label}: {time_now}"

    async def send_code(self, email_data: dict[str, Any]) -> bool:
        """Send auth code/link to all allowed users.

        Returns:
            bool: True if sent to at least one user successfully
        """
        time_now = datetime.now().strftime("%H:%M:%S")
        auth_data = email_data.get("auth_data")

        if auth_data:
            message = self._format_auth_message(auth_data, time_now)
        else:
            subject = email_data.get("subject", t("no_subject"))
            message = (
                f"{t('new_email_header')}\n\n"
                f"{t('subject_label')}: {subject}\n"
                f"{t('time_label')}: {time_now}\n\n"
                f"{t('extraction_failed')}"
            )

        return await self._broadcast(message) > 0

    async def send_startup_message(self) -> None:
        """Send bot startup message."""
        message = (
            f"{t('bot_started')}\n\n"
            f"{t('checking_email_interval', interval=config.CHECK_INTERVAL)}\n"
            f"{t('waiting_for_emails')}"
        )
        await self._broadcast(message, log_success=False)
