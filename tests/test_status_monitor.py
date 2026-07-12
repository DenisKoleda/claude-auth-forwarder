import asyncio

from admin_state import AdminState
from state_store import StateStore
from status_monitor import OpenAIStatusMonitor


class FakeNotifier:
    def __init__(self) -> None:
        self.ids: list[str] = []

    async def sync_incident(self, incident):
        self.ids.append(incident["id"])
        return True


def test_status_sync_sends_active_and_only_tracked_resolved(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr("settings.ADMIN_STATE_FILE", str(tmp_path / "admin.json"))
    state = AdminState()
    store = StateStore(str(tmp_path / "state.db"))
    store.record_incident_message("tracked", 10, 100, "u1", "investigating")
    notifier = FakeNotifier()
    monitor = OpenAIStatusMonitor(state, store, notifier)  # type: ignore[arg-type]

    async def fake_fetch():
        return [
            {"id": "active", "status": "investigating"},
            {"id": "tracked", "status": "resolved"},
            {"id": "old", "status": "resolved"},
        ]

    monitor.fetch_incidents = fake_fetch  # type: ignore[method-assign]
    assert asyncio.run(monitor.sync()) == 2
    assert notifier.ids == ["active", "tracked"]
    store.close()
