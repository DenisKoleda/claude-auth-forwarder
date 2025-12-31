import logging
from datetime import datetime
from typing import Any

from telegram import Bot
from telegram.error import TelegramError

import config

logger = logging.getLogger(__name__)


class TelegramNotifier:
    def __init__(self) -> None:
        self.bot = Bot(token=config.TELEGRAM_BOT_TOKEN)

    async def _broadcast(self, message: str, log_success: bool = True) -> int:
        """Отправить сообщение всем разрешённым пользователям.

        Args:
            message: Текст сообщения
            log_success: Логировать успешные отправки

        Returns:
            int: Количество успешных отправок
        """
        success_count = 0
        for user_id in config.ALLOWED_USER_IDS:
            try:
                await self.bot.send_message(chat_id=user_id, text=message)
                if log_success:
                    logger.info(f"Сообщение отправлено пользователю {user_id}")
                success_count += 1
            except TelegramError as e:
                logger.error(f"Ошибка отправки пользователю {user_id}: {e}")
        return success_count

    def _format_auth_message(self, auth_data: dict[str, str], time_now: str) -> str:
        """Форматировать сообщение с auth данными."""
        if auth_data['type'] == 'link':
            return (
                f"🔐 Ссылка для входа в Claude\n\n"
                f"Время: {time_now}\n\n"
                f"{auth_data['value']}"
            )
        return (
            f"🔐 Код авторизации Claude\n\n"
            f"Код: {auth_data['value']}\n"
            f"Время: {time_now}"
        )

    async def send_code(self, email_data: dict[str, Any]) -> bool:
        """Отправить код/ссылку авторизации всем разрешённым пользователям.

        Returns:
            bool: True если хотя бы одному пользователю успешно отправлено
        """
        time_now = datetime.now().strftime("%H:%M:%S")
        auth_data = email_data.get('auth_data')

        if auth_data:
            message = self._format_auth_message(auth_data, time_now)
        else:
            message = (
                f"📧 Новое письмо от Claude/Anthropic\n\n"
                f"Тема: {email_data.get('subject', 'Без темы')}\n"
                f"Время: {time_now}\n\n"
                f"Не удалось извлечь код/ссылку. Проверьте почту вручную."
            )

        return await self._broadcast(message) > 0

    async def send_startup_message(self) -> None:
        """Отправить сообщение о запуске бота"""
        message = (
            f"✅ Бот запущен!\n\n"
            f"Проверяю почту каждые {config.CHECK_INTERVAL} сек.\n"
            f"Жду писем от Claude/Anthropic..."
        )
        await self._broadcast(message, log_success=False)
