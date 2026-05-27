import logging
from pathlib import Path
from typing import Any

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import Application, CallbackQueryHandler, CommandHandler, ContextTypes
from telegram.request import HTTPXRequest

import config
from admin_state import AdminState

logger = logging.getLogger(__name__)

PROVIDER_LABELS = {
    "claude": "Claude",
    "openai": "OpenAI",
}


class TelegramAdmin:
    def __init__(self, state: AdminState) -> None:
        self.state = state
        self.admin_user_ids = set(getattr(config, "ADMIN_USER_IDS", []))
        if not self.admin_user_ids:
            self.admin_user_ids = set(getattr(config, "ALLOWED_USER_IDS", []))

        builder = Application.builder().token(config.TELEGRAM_BOT_TOKEN)
        base_url = getattr(config, "TELEGRAM_BASE_URL", "")
        proxy_url = getattr(config, "TELEGRAM_PROXY_URL", "")
        if base_url:
            builder = builder.base_url(base_url)
        if proxy_url:
            builder = builder.request(HTTPXRequest(proxy=proxy_url))
            builder = builder.get_updates_request(HTTPXRequest(proxy=proxy_url))

        self.app = builder.build()
        self.app.add_handler(CommandHandler("admin", self._admin_command))
        self.app.add_handler(CommandHandler("broadcast", self._broadcast_command))
        self.app.add_handler(CommandHandler("broadcast_image", self._broadcast_image_command))
        self.app.add_handler(CommandHandler("images", self._images_command))
        self.app.add_handler(CallbackQueryHandler(self._handle_callback, pattern=r"^admin:"))

    def _is_admin(self, update: Update) -> bool:
        user = update.effective_user
        return bool(user and user.id in self.admin_user_ids)

    def _status_text(self) -> str:
        statuses = self.state.provider_statuses()
        lines = ["Админка пересылки кодов", ""]
        for provider_id, label in PROVIDER_LABELS.items():
            state = "включен" if statuses[provider_id] else "выключен"
            lines.append(f"{label}: {state}")
        return "\n".join(lines)

    def _keyboard(self) -> InlineKeyboardMarkup:
        statuses = self.state.provider_statuses()
        rows: list[list[InlineKeyboardButton]] = []
        for provider_id, label in PROVIDER_LABELS.items():
            marker = "✅" if statuses[provider_id] else "⛔"
            rows.append(
                [
                    InlineKeyboardButton(
                        f"{marker} {label}", callback_data=f"admin:toggle:{provider_id}"
                    )
                ]
            )
        rows.append([InlineKeyboardButton("Обновить", callback_data="admin:refresh")])
        return InlineKeyboardMarkup(rows)

    def _image_dir(self) -> Path:
        return Path(getattr(config, "ADMIN_IMAGE_DIR", "assets/messages"))

    def _image_path(self, image_name: str) -> Path | None:
        clean_name = image_name.strip().lower()
        if not clean_name:
            return None
        if not clean_name.endswith(".png"):
            clean_name += ".png"
        image_path = self._image_dir() / clean_name
        try:
            image_path.resolve().relative_to(self._image_dir().resolve())
        except ValueError:
            return None
        return image_path if image_path.exists() else None

    def _image_names(self) -> list[str]:
        image_dir = self._image_dir()
        if not image_dir.exists():
            return []
        return sorted(path.stem for path in image_dir.glob("*.png"))

    async def _reply_access_denied(self, update: Update) -> None:
        if update.message:
            await update.message.reply_text("Нет доступа.")

    async def _send_broadcast_text(self, text: str) -> tuple[int, int]:
        success = 0
        failed = 0
        for user_id in getattr(config, "ALLOWED_USER_IDS", []):
            try:
                await self.app.bot.send_message(chat_id=user_id, text=text)
                success += 1
            except Exception as e:
                failed += 1
                logger.error("Broadcast send failed for %s: %s", user_id, e)
        return success, failed

    async def _send_broadcast_image(self, image_path: Path, caption: str) -> tuple[int, int]:
        success = 0
        failed = 0
        for user_id in getattr(config, "ALLOWED_USER_IDS", []):
            try:
                with image_path.open("rb") as image_file:
                    await self.app.bot.send_photo(
                        chat_id=user_id,
                        photo=image_file,
                        caption=caption,
                        connect_timeout=30,
                        read_timeout=30,
                        write_timeout=30,
                        pool_timeout=30,
                    )
                success += 1
            except Exception as e:
                failed += 1
                logger.error("Image broadcast send failed for %s: %s", user_id, e)
        return success, failed

    async def _admin_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        del context
        if not self._is_admin(update):
            await self._reply_access_denied(update)
            return

        if update.message:
            await update.message.reply_text(self._status_text(), reply_markup=self._keyboard())

    async def _broadcast_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        if not self._is_admin(update):
            await self._reply_access_denied(update)
            return

        text = " ".join(context.args).strip()
        if not text:
            if update.message:
                await update.message.reply_text("Использование: /broadcast текст сообщения")
            return

        success, failed = await self._send_broadcast_text(text)
        if update.message:
            await update.message.reply_text(f"Отправлено: {success}, ошибок: {failed}")

    async def _broadcast_image_command(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE
    ) -> None:
        if not self._is_admin(update):
            await self._reply_access_denied(update)
            return

        if len(context.args) < 2:
            if update.message:
                await update.message.reply_text(
                    "Использование: /broadcast_image auth|billing|broadcast текст сообщения"
                )
            return

        image_name = context.args[0]
        caption = " ".join(context.args[1:]).strip()
        image_path = self._image_path(image_name)
        if not image_path:
            if update.message:
                await update.message.reply_text(
                    "Картинка не найдена. Доступные: " + ", ".join(self._image_names())
                )
            return

        success, failed = await self._send_broadcast_image(image_path, caption)
        if update.message:
            await update.message.reply_text(f"Картинка отправлена: {success}, ошибок: {failed}")

    async def _images_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        del context
        if not self._is_admin(update):
            await self._reply_access_denied(update)
            return
        names = self._image_names()
        text = "Доступные картинки: " + (", ".join(names) if names else "нет")
        if update.message:
            await update.message.reply_text(text)

    async def _handle_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        del context
        query = update.callback_query
        if not query:
            return

        if not self._is_admin(update):
            await query.answer("Нет доступа.", show_alert=True)
            return

        data = query.data or ""
        parts = data.split(":")
        if len(parts) == 3 and parts[1] == "toggle":
            provider_id = parts[2]
            try:
                enabled = self.state.toggle_provider(provider_id)
            except ValueError:
                await query.answer("Неизвестный провайдер.", show_alert=True)
                return
            label = PROVIDER_LABELS.get(provider_id, provider_id)
            await query.answer(f"{label}: {'включен' if enabled else 'выключен'}")
            logger.info("Admin toggled %s to %s", provider_id, enabled)
        else:
            await query.answer("Обновлено")

        await query.edit_message_text(self._status_text(), reply_markup=self._keyboard())

    async def start(self) -> None:
        await self.app.initialize()
        await self.app.start()
        await self.app.updater.start_polling(allowed_updates=["message", "callback_query"])
        logger.info("Telegram admin started for user ids: %s", sorted(self.admin_user_ids))

    async def stop(self) -> None:
        updater: Any = self.app.updater
        if updater and updater.running:
            await updater.stop()
        await self.app.stop()
        await self.app.shutdown()
