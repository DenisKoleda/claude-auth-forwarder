import asyncio
from types import SimpleNamespace
from typing import Any
from zoneinfo import ZoneInfo

import settings
from state_store import StateStore
from telegram_bot import TelegramNotifier


class FakeBot:
    def __init__(self, failing: set[int] | None = None) -> None:
        self.failing = failing or set()
        self.sent: list[int] = []
        self.edited: list[tuple[int, int]] = []

    async def send_message(self, chat_id: int, **kwargs):
        del kwargs
        self.sent.append(chat_id)
        if chat_id in self.failing:
            from telegram.error import TimedOut

            raise TimedOut("timeout")
        return SimpleNamespace(message_id=chat_id + 1000)

    async def edit_message_text(self, chat_id: int, message_id: int, **kwargs):
        del kwargs
        self.edited.append((chat_id, message_id))
        return True


def notifier_with_fake(store: StateStore, bot: FakeBot) -> TelegramNotifier:
    notifier = object.__new__(TelegramNotifier)
    notifier.bot = bot  # type: ignore[assignment]
    notifier.store = store
    notifier.timezone = ZoneInfo("Europe/Saratov")
    return notifier


def test_partial_delivery_retries_only_failed_recipient(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr(settings, "AUTH_RECIPIENT_IDS", [10, 20])
    store = StateStore(str(tmp_path / "state.db"))
    first_bot = FakeBot({20})
    notifier = notifier_with_fake(store, first_bot)
    email = {
        "id": "abc",
        "auth_data": {"type": "code", "value": "123456", "provider_name": "OpenAI"},
    }

    assert asyncio.run(notifier.deliver_email(email)) is False
    assert first_bot.sent == [10, 20]

    second_bot = FakeBot()
    notifier.bot = second_bot  # type: ignore[assignment]
    assert asyncio.run(notifier.deliver_email(email)) is True
    assert second_bot.sent == [20]
    store.close()


def test_incident_update_edits_existing_message(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr(settings, "INCIDENT_RECIPIENT_IDS", [10])
    store = StateStore(str(tmp_path / "state.db"))
    bot = FakeBot()
    notifier = notifier_with_fake(store, bot)
    incident: dict[str, Any] = {
        "id": "incident-1",
        "name": "Elevated errors",
        "status": "investigating",
        "impact": "minor",
        "created_at": "2026-07-12T09:49:34Z",
        "updated_at": "2026-07-12T10:00:00Z",
        "incident_updates": [
            {
                "id": "update-1",
                "status": "investigating",
                "body": "We are investigating.",
                "updated_at": "2026-07-12T10:00:00Z",
            }
        ],
    }
    assert asyncio.run(notifier.sync_incident(incident)) is True
    assert bot.sent == [10]

    incident["incident_updates"][0] = {
        "id": "update-2",
        "status": "identified",
        "body": "Cause identified.",
        "updated_at": "2026-07-12T10:10:00Z",
    }
    assert asyncio.run(notifier.sync_incident(incident)) is True
    assert bot.sent == [10]
    assert bot.edited == [(10, 1010)]
    store.close()
