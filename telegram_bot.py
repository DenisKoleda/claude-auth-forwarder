import logging
from datetime import datetime
from pathlib import Path
from typing import Any

from telegram import Bot
from telegram.error import TelegramError
from telegram.request import HTTPXRequest

import config
from i18n import t

logger = logging.getLogger(__name__)


class TelegramNotifier:
    def __init__(self) -> None:
        base_url = getattr(config, "TELEGRAM_BASE_URL", "")
        proxy_url = getattr(config, "TELEGRAM_PROXY_URL", "")
        bot_kwargs: dict[str, Any] = {"token": config.TELEGRAM_BOT_TOKEN}
        if base_url:
            bot_kwargs["base_url"] = base_url
        if proxy_url:
            bot_kwargs["request"] = HTTPXRequest(proxy=proxy_url)
        self.bot = Bot(**bot_kwargs)

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

    def _format_payment_message(self, payment_data: dict[str, str], time_now: str) -> str:
        """Format message for any payment-related event."""
        time_line = f"{t('time_label')}: {time_now}"
        ptype = payment_data.get("type")
        provider_name = payment_data.get("provider_name", "Claude")

        if ptype == "openai_api_funded":
            return (
                f"{t('openai_api_funded_header')}\n\n"
                f"{t('payment_amount')}: {payment_data['amount']}\n"
                f"{t('payment_card')}: •••• {payment_data['card_last4']}\n"
                f"{time_line}\n\n"
                f"{t('openai_billing_action')}"
            )

        if ptype == "openai_usage_limits_increased":
            return (
                f"{t('openai_usage_limits_header')}\n\n"
                f"{time_line}\n\n"
                f"{t('openai_billing_action')}"
            )

        if ptype == "subscription_cancel_pending":
            lines = [t("subscription_cancel_pending_header", provider=provider_name), ""]
            if payment_data.get("plan"):
                lines.append(f"{t('payment_plan')}: {payment_data['plan']}")
            if payment_data.get("period"):
                lines.append(f"{t('payment_period')}: {payment_data['period']}")
            lines.append(time_line)
            lines.extend(["", t("openai_subscription_action")])
            return "\n".join(lines)

        if ptype == "subscription_started":
            lines = [t("subscription_started_header", provider=provider_name), ""]
            if payment_data.get("plan"):
                lines.append(f"{t('payment_plan')}: {payment_data['plan']}")
            if payment_data.get("amount"):
                lines.append(f"{t('payment_amount')}: {payment_data['amount']}")
            lines.append(f"{t('payment_card')}: •••• {payment_data['card_last4']}")
            lines.append(time_line)
            return "\n".join(lines)

        if ptype == "payment_success":
            lines = [t("payment_success_header", provider=provider_name), ""]
            lines.append(f"{t('payment_amount')}: {payment_data['amount']}")
            if payment_data.get("plan"):
                lines.append(f"{t('payment_plan')}: {payment_data['plan']}")
            if payment_data.get("period"):
                lines.append(f"{t('payment_period')}: {payment_data['period']}")
            lines.append(f"{t('payment_card')}: •••• {payment_data['card_last4']}")
            if payment_data.get("receipt_number"):
                lines.append(f"{t('payment_receipt_number')}: {payment_data['receipt_number']}")
            lines.append(time_line)
            return "\n".join(lines)

        if ptype == "subscription_paused":
            return (
                f"{t('subscription_paused_header', provider=provider_name)}\n\n"
                f"{t('subscription_paused_body')}\n"
                f"{time_line}\n\n"
                f"{t('payment_action')}"
            )

        # payment_failed (default)
        return (
            f"{t('payment_failed_header', provider=provider_name)}\n\n"
            f"{t('payment_amount')}: {payment_data['amount']}\n"
            f"{t('payment_card')}: •••• {payment_data['card_last4']}\n"
            f"{time_line}\n\n"
            f"{t('payment_action')}"
        )

    def _format_auth_message(self, auth_data: dict[str, str], time_now: str) -> str:
        """Format message with auth data."""
        time_label = t("time_label")
        provider_name = auth_data.get("provider_name", "Claude")
        if auth_data["type"] == "link":
            header = t("auth_link_header", provider=provider_name)
            return f"{header}\n\n{time_label}: {time_now}\n\n{auth_data['value']}"
        if auth_data["type"] == "mobile_link":
            header = t("auth_mobile_link_header", provider=provider_name)
            return f"{header}\n\n{time_label}: {time_now}\n\n{auth_data['value']}"
        header = t("auth_code_header", provider=provider_name)
        code_label = t("code_label")
        return f"{header}\n\n{code_label}: {auth_data['value']}\n{time_label}: {time_now}"

    async def send_code(self, email_data: dict[str, Any]) -> bool:
        """Send auth code/link to all allowed users.

        Returns:
            bool: True if sent to at least one user successfully
        """
        time_now = datetime.now().strftime("%H:%M:%S")
        auth_data = email_data.get("auth_data")
        payment_data = email_data.get("payment_data")

        if auth_data:
            message = self._format_auth_message(auth_data, time_now)
        elif payment_data:
            message = self._format_payment_message(payment_data, time_now)
        else:
            subject = email_data.get("subject", t("no_subject"))
            provider_name = email_data.get("provider_name", "Claude/Anthropic")
            message = (
                f"{t('new_email_header', provider=provider_name)}\n\n"
                f"{t('subject_label')}: {subject}\n"
                f"{t('time_label')}: {time_now}\n\n"
                f"{t('extraction_failed')}"
            )

        return await self._broadcast(message) > 0

    async def send_token_expired_message(self) -> None:
        """Send notification that Gmail token has expired."""
        message = (
            f"{t('token_expired_tg_header')}\n\n"
            f"{t('token_expired_tg_body')}\n\n"
            f"{t('token_expired_tg_action')}"
        )
        await self._broadcast(message)

    async def send_startup_message(self) -> None:
        """Send bot startup message."""
        message = (
            f"{t('bot_started')}\n\n"
            f"{t('checking_email_interval', interval=config.CHECK_INTERVAL)}\n"
            f"{t('waiting_for_emails')}"
        )
        await self._broadcast(message, log_success=False)

    async def send_custom_message(self, user_id: int, message: str) -> bool:
        """Send one custom message to a specific user."""
        try:
            await self.bot.send_message(chat_id=user_id, text=message)
            return True
        except TelegramError as e:
            logger.error(t("msg_send_error", user_id=user_id, error=e))
            return False

    async def send_custom_image(self, user_id: int, image_path: Path, caption: str) -> bool:
        """Send one image with caption to a specific user."""
        try:
            with image_path.open("rb") as image_file:
                await self.bot.send_photo(
                    chat_id=user_id,
                    photo=image_file,
                    caption=caption,
                    connect_timeout=30,
                    read_timeout=30,
                    write_timeout=30,
                    pool_timeout=30,
                )
            return True
        except TelegramError as e:
            logger.error(t("msg_send_error", user_id=user_id, error=e))
            return False
