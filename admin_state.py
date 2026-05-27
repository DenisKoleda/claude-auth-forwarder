import json
import logging
import threading
from pathlib import Path
from typing import Any

import config

logger = logging.getLogger(__name__)


class AdminState:
    """Persisted runtime switches controlled from Telegram admin UI."""

    def __init__(self) -> None:
        self.path = Path(getattr(config, "ADMIN_STATE_FILE", "data/admin_state.json"))
        self._lock = threading.RLock()
        self._state = self._load()

    def _default_state(self) -> dict[str, Any]:
        return {
            "providers": {
                "claude": bool(getattr(config, "ENABLE_CLAUDE_EMAILS", True)),
                "openai": bool(getattr(config, "ENABLE_OPENAI_EMAILS", True)),
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

        providers = loaded.get("providers", {})
        default_state["providers"].update(
            {
                "claude": bool(providers.get("claude", default_state["providers"]["claude"])),
                "openai": bool(providers.get("openai", default_state["providers"]["openai"])),
            }
        )
        return default_state

    def _save_locked(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        temp_path = self.path.with_suffix(".tmp")
        temp_path.write_text(json.dumps(self._state, indent=2, sort_keys=True))
        temp_path.replace(self.path)

    def is_provider_enabled(self, provider_id: str) -> bool:
        with self._lock:
            return bool(self._state.get("providers", {}).get(provider_id, False))

    def set_provider_enabled(self, provider_id: str, enabled: bool) -> bool:
        if provider_id not in {"claude", "openai"}:
            raise ValueError(f"Unknown provider: {provider_id}")

        with self._lock:
            self._state.setdefault("providers", {})[provider_id] = enabled
            self._save_locked()
            return enabled

    def toggle_provider(self, provider_id: str) -> bool:
        with self._lock:
            enabled = not self.is_provider_enabled(provider_id)
            return self.set_provider_enabled(provider_id, enabled)

    def provider_statuses(self) -> dict[str, bool]:
        with self._lock:
            providers = self._state.get("providers", {})
            return {
                "claude": bool(providers.get("claude", False)),
                "openai": bool(providers.get("openai", False)),
            }
