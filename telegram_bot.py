import html
import logging
from datetime import datetime
from typing import Any
from zoneinfo import ZoneInfo

from telegram import Bot, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.error import BadRequest, TelegramError
from telegram.request import HTTPXRequest

import settings
from i18n import t
from state_store import StateStore

logger = logging.getLogger(__name__)

STATUS_LABELS = {
    "investigating": "Расследуется",
    "identified": "Причина найдена",
    "monitoring": "Исправление применено, наблюдаем",
    "resolved": "Решён",
    "postmortem": "Разбор опубликован",
}
IMPACT_LABELS = {
    "none": "нет",
    "minor": "небольшое",
    "major": "значительное",
    "critical": "критическое",
}
STATUS_ICONS = {
    "investigating": "🟠",
    "identified": "🟠",
    "monitoring": "🟡",
    "resolved": "✅",
    "postmortem": "📄",
}


class TelegramNotifier:
    def __init__(self, store: StateStore) -> None:
        base_url = settings.TELEGRAM_BASE_URL
        proxy_url = settings.TELEGRAM_PROXY_URL
        bot_kwargs: dict[str, Any] = {"token": settings.TELEGRAM_BOT_TOKEN}
        if base_url:
            bot_kwargs["base_url"] = base_url
        if proxy_url:
            bot_kwargs["request"] = HTTPXRequest(proxy=proxy_url)
        self.bot = Bot(**bot_kwargs)
        self.store = store
        self.timezone = ZoneInfo(settings.DISPLAY_TIMEZONE)

    def _recipient_ids(self, email_data: dict[str, Any]) -> list[int]:
        if email_data.get("auth_data"):
            return settings.AUTH_RECIPIENT_IDS
        if email_data.get("payment_data"):
            return settings.BILLING_RECIPIENT_IDS
        return settings.GENERAL_RECIPIENT_IDS

    async def _broadcast(
        self, message: str, recipient_ids: list[int], log_success: bool = True
    ) -> int:
        success_count = 0
        for user_id in recipient_ids:
            try:
                await self.bot.send_message(chat_id=user_id, text=message)
                if log_success:
                    logger.info(t("msg_sent_to_user", user_id=user_id))
                success_count += 1
            except TelegramError as exc:
                logger.error(t("msg_send_error", user_id=user_id, error=exc))
        return success_count

    def _format_payment_message(self, payment_data: dict[str, str], time_now: str) -> str:
        time_line = f"{t('time_label')}: {time_now}"
        ptype = payment_data.get("type")
        provider_name = payment_data.get("provider_name", "Claude")

        if ptype == "openai_api_funded":
            return (
                f"{t('openai_api_funded_header')}\n\n"
                f"{t('payment_amount')}: {payment_data['amount']}\n"
                f"{t('payment_card')}: •••• {payment_data['card_last4']}\n"
                f"{time_line}\n\n{t('openai_billing_action')}"
            )
        if ptype == "openai_usage_limits_increased":
            return (
                f"{t('openai_usage_limits_header')}\n\n{time_line}\n\n{t('openai_billing_action')}"
            )
        if ptype == "subscription_cancel_pending":
            lines = [t("subscription_cancel_pending_header", provider=provider_name), ""]
            if payment_data.get("plan"):
                lines.append(f"{t('payment_plan')}: {payment_data['plan']}")
            if payment_data.get("period"):
                lines.append(f"{t('payment_period')}: {payment_data['period']}")
            lines.extend([time_line, "", t("openai_subscription_action")])
            return "\n".join(lines)
        if ptype == "subscription_started":
            lines = [t("subscription_started_header", provider=provider_name), ""]
            if payment_data.get("plan"):
                lines.append(f"{t('payment_plan')}: {payment_data['plan']}")
            if payment_data.get("amount"):
                lines.append(f"{t('payment_amount')}: {payment_data['amount']}")
            lines.extend([f"{t('payment_card')}: •••• {payment_data['card_last4']}", time_line])
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
                f"{t('subscription_paused_body')}\n{time_line}\n\n{t('payment_action')}"
            )
        return (
            f"{t('payment_failed_header', provider=provider_name)}\n\n"
            f"{t('payment_amount')}: {payment_data['amount']}\n"
            f"{t('payment_card')}: •••• {payment_data['card_last4']}\n"
            f"{time_line}\n\n{t('payment_action')}"
        )

    def _format_auth_message(
        self, auth_data: dict[str, str], time_now: str
    ) -> tuple[str, InlineKeyboardMarkup | None]:
        provider_name = auth_data.get("provider_name", "Claude")
        auth_type = auth_data["type"]
        if auth_type in {"link", "mobile_link"}:
            header_key = (
                "auth_mobile_link_header" if auth_type == "mobile_link" else "auth_link_header"
            )
            text = f"{t(header_key, provider=provider_name)}\n\n{t('time_label')}: {time_now}"
            keyboard = InlineKeyboardMarkup(
                [[InlineKeyboardButton(f"Открыть {provider_name}", url=auth_data["value"])]]
            )
            return text, keyboard
        return (
            f"{t('auth_code_header', provider=provider_name)}\n\n"
            f"{t('code_label')}: {auth_data['value']}\n{t('time_label')}: {time_now}",
            None,
        )

    def _format_email(self, email_data: dict[str, Any]) -> tuple[str, InlineKeyboardMarkup | None]:
        time_now = datetime.now(self.timezone).strftime("%H:%M:%S")
        if email_data.get("auth_data"):
            return self._format_auth_message(email_data["auth_data"], time_now)
        if email_data.get("payment_data"):
            return self._format_payment_message(email_data["payment_data"], time_now), None
        subject = email_data.get("subject", t("no_subject"))
        provider_name = email_data.get("provider_name", "Claude/OpenAI")
        return (
            f"{t('new_email_header', provider=provider_name)}\n\n"
            f"{t('subject_label')}: {subject}\n{t('time_label')}: {time_now}\n\n"
            f"{t('extraction_failed')}",
            None,
        )

    async def deliver_email(self, email_data: dict[str, Any]) -> bool:
        source_id = f"gmail:{email_data['id']}"
        recipients = list(dict.fromkeys(self._recipient_ids(email_data)))
        delivered = self.store.delivered_recipients(source_id)
        message, keyboard = self._format_email(email_data)

        for user_id in recipients:
            if user_id in delivered:
                continue
            try:
                sent = await self.bot.send_message(
                    chat_id=user_id,
                    text=message,
                    reply_markup=keyboard,
                    protect_content=bool(email_data.get("auth_data")),
                )
                self.store.record_delivery(source_id, user_id, True, sent.message_id)
                logger.info(t("msg_sent_to_user", user_id=user_id))
            except TelegramError as exc:
                self.store.record_delivery(source_id, user_id, False, error=str(exc))
                logger.error(t("msg_send_error", user_id=user_id, error=exc))

        return set(recipients).issubset(self.store.delivered_recipients(source_id))

    def _parse_timestamp(self, value: str) -> datetime:
        return datetime.fromisoformat(value.replace("Z", "+00:00")).astimezone(self.timezone)

    def format_incident_message(self, incident: dict[str, Any]) -> str:
        updates = incident.get("incident_updates") or []
        latest = updates[0] if updates else {}
        status = str(latest.get("status") or incident.get("status") or "investigating").lower()
        icon = STATUS_ICONS.get(status, "⚠️")
        status_label = STATUS_LABELS.get(status, status)
        impact = IMPACT_LABELS.get(str(incident.get("impact", "none")), "неизвестно")
        started = self._parse_timestamp(incident["created_at"]).strftime("%d.%m.%Y %H:%M")
        updated = self._parse_timestamp(
            latest.get("display_at") or latest.get("updated_at") or incident["updated_at"]
        ).strftime("%d.%m.%Y %H:%M")
        title = html.escape(str(incident.get("name", "Инцидент OpenAI")))
        body = html.escape(str(latest.get("body", "Нет подробностей.")))

        return (
            f"{icon} <b>{title}</b>\n\n"
            f"<b>Статус:</b> {html.escape(status_label)}\n"
            f"<b>Влияние:</b> {html.escape(impact)}\n"
            f"<b>Началось:</b> {started}\n"
            f"<b>Обновлено:</b> {updated}\n\n{body}"
        )

    async def sync_incident(self, incident: dict[str, Any]) -> bool:
        incident_id = str(incident["id"])
        updates = incident.get("incident_updates") or []
        latest = updates[0] if updates else {}
        update_id = str(latest.get("id") or incident.get("updated_at"))
        status = str(latest.get("status") or incident.get("status") or "unknown")
        message = self.format_incident_message(incident)
        incident_url = f"{settings.OPENAI_STATUS_PAGE_URL}/incidents/{incident_id}"
        keyboard = InlineKeyboardMarkup(
            [[InlineKeyboardButton("Открыть инцидент", url=incident_url)]]
        )
        success = True

        for user_id in settings.INCIDENT_RECIPIENT_IDS:
            existing = self.store.get_incident_message(incident_id, user_id)
            if existing and existing["last_update_id"] == update_id:
                continue
            try:
                if existing:
                    try:
                        await self.bot.edit_message_text(
                            chat_id=user_id,
                            message_id=int(existing["telegram_message_id"]),
                            text=message,
                            parse_mode="HTML",
                            reply_markup=keyboard,
                        )
                        message_id = int(existing["telegram_message_id"])
                    except BadRequest as exc:
                        if "message is not modified" in str(exc).lower():
                            message_id = int(existing["telegram_message_id"])
                        else:
                            sent = await self.bot.send_message(
                                chat_id=user_id,
                                text=message,
                                parse_mode="HTML",
                                reply_markup=keyboard,
                            )
                            message_id = sent.message_id
                else:
                    sent = await self.bot.send_message(
                        chat_id=user_id,
                        text=message,
                        parse_mode="HTML",
                        reply_markup=keyboard,
                    )
                    message_id = sent.message_id
                self.store.record_incident_message(
                    incident_id, user_id, message_id, update_id, status
                )
            except TelegramError as exc:
                success = False
                logger.error("Incident delivery failed for %s: %s", user_id, exc)
        return success

    async def send_token_expired_message(self) -> None:
        message = (
            f"{t('token_expired_tg_header')}\n\n{t('token_expired_tg_body')}\n\n"
            f"{t('token_expired_tg_action')}"
        )
        await self._broadcast(message, settings.ADMIN_USER_IDS)

    async def send_startup_message(self) -> None:
        message = (
            f"{t('bot_started')}\n\n"
            f"{t('checking_email_interval', interval=settings.CHECK_INTERVAL)}\n"
            f"{t('waiting_for_emails')}"
        )
        await self._broadcast(message, settings.ADMIN_USER_IDS, log_success=False)

    async def send_custom_message(self, user_id: int, message: str) -> bool:
        try:
            await self.bot.send_message(chat_id=user_id, text=message)
            return True
        except TelegramError as exc:
            logger.error(t("msg_send_error", user_id=user_id, error=exc))
            return False
