"""Docker healthcheck based on real application progress."""

from __future__ import annotations

import sys
import time

import settings
from state_store import StateStore


def main() -> int:
    store = StateStore(settings.STATE_DB_FILE)
    snapshot = store.health_snapshot()
    store.close()
    now = time.time()

    required = {"heartbeat": settings.HEALTH_MAX_HEARTBEAT_AGE}
    if settings.ENABLE_CLAUDE_EMAILS or settings.ENABLE_OPENAI_EMAILS:
        required["gmail"] = settings.HEALTH_MAX_GMAIL_AGE
    if settings.ENABLE_OPENAI_INCIDENTS:
        required["openai_status"] = settings.HEALTH_MAX_STATUS_AGE

    failures = []
    for name, max_age in required.items():
        item = snapshot.get(name)
        if not item:
            failures.append(f"{name}=missing")
            continue
        age = now - float(item["timestamp"])
        if age > max_age:
            failures.append(f"{name}=stale:{age:.0f}s")

    if failures:
        print("UNHEALTHY " + " ".join(failures))
        return 1
    print("OK")
    return 0


if __name__ == "__main__":
    sys.exit(main())
