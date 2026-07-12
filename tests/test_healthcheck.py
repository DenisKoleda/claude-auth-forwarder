import time

import healthcheck
import settings
from state_store import StateStore


def test_healthcheck_uses_real_progress(tmp_path, monkeypatch) -> None:
    database = str(tmp_path / "state.db")
    monkeypatch.setattr(settings, "STATE_DB_FILE", database)
    monkeypatch.setattr(settings, "ENABLE_CLAUDE_EMAILS", True)
    monkeypatch.setattr(settings, "ENABLE_OPENAI_EMAILS", True)
    monkeypatch.setattr(settings, "ENABLE_OPENAI_INCIDENTS", True)
    store = StateStore(database)
    for key in ("heartbeat", "gmail", "openai_status"):
        store.touch_health(key, "ok")
    store.close()
    assert healthcheck.main() == 0


def test_healthcheck_rejects_stale_heartbeat(tmp_path, monkeypatch) -> None:
    database = str(tmp_path / "state.db")
    monkeypatch.setattr(settings, "STATE_DB_FILE", database)
    monkeypatch.setattr(settings, "ENABLE_CLAUDE_EMAILS", False)
    monkeypatch.setattr(settings, "ENABLE_OPENAI_EMAILS", False)
    monkeypatch.setattr(settings, "ENABLE_OPENAI_INCIDENTS", False)
    monkeypatch.setattr(settings, "HEALTH_MAX_HEARTBEAT_AGE", 1)
    now = time.time()
    store = StateStore(database)
    store.touch_health("heartbeat", "old")
    store.close()
    monkeypatch.setattr(healthcheck.time, "time", lambda: now + 10)
    assert healthcheck.main() == 1
