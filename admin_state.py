import json
import logging
import threading
from pathlib import Path
from typing import Any

import settings
from secure_files import write_private_text

logger = logging.getLogger(__name__)


class AdminState:
    """Persisted runtime switches controlled from Telegram admin UI."""

    def __init__(self) -> None:
        self.path = Path(settings.ADMIN_STATE_FILE)
        self._lock = threading.RLock()
        self._state = self._load()

    def _default_state(self) -> dict[str, Any]:
        return {
            "sources": {
                "claude_auth": settings.ENABLE_CLAUDE_EMAILS,
                "openai_auth": settings.ENABLE_OPENAI_EMAILS,
                "billing": settings.ENABLE_BILLING_EMAILS,
                "incidents": settings.ENABLE_OPENAI_INCIDENTS,
            }
        }

    def _load(self) -> dict[str, Any]:
        default_state = self._default_state()
        if not self.path.exists():
            return default_state

        try:
            loaded = json.loads(self.path.read_text())
        except (OSError, json.JSONDecodeError) as e:
            logger.warning("Could not read admin state, using defaults: %s", e)
            return default_state

        sources = loaded.get("sources", {})
        legacy = loaded.get("providers", {})
        if "claude" in legacy:
            sources.setdefault("claude_auth", legacy["claude"])
        if "openai" in legacy:
            sources.setdefault("openai_auth", legacy["openai"])
        for source_id in default_state["sources"]:
            if source_id in sources:
                default_state["sources"][source_id] = bool(sources[source_id])
        return default_state

    def _save_locked(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        write_private_text(self.path, json.dumps(self._state, indent=2, sort_keys=True))

    def is_source_enabled(self, source_id: str) -> bool:
        with self._lock:
            return bool(self._state.get("sources", {}).get(source_id, False))

    def set_source_enabled(self, source_id: str, enabled: bool) -> bool:
        if source_id not in {"claude_auth", "openai_auth", "billing", "incidents"}:
            raise ValueError(f"Unknown source: {source_id}")

        with self._lock:
            self._state.setdefault("sources", {})[source_id] = enabled
            self._save_locked()
            return enabled

    def toggle_source(self, source_id: str) -> bool:
        with self._lock:
            enabled = not self.is_source_enabled(source_id)
            return self.set_source_enabled(source_id, enabled)

    def source_statuses(self) -> dict[str, bool]:
        with self._lock:
            sources = self._state.get("sources", {})
            return {
                source_id: bool(sources.get(source_id, False))
                for source_id in ("claude_auth", "openai_auth", "billing", "incidents")
            }
