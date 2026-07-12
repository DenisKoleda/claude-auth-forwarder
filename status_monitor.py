"""OpenAI Status JSON API integration."""

from __future__ import annotations

import logging
from typing import Any

import httpx

import settings
from admin_state import AdminState
from state_store import StateStore
from telegram_bot import TelegramNotifier

logger = logging.getLogger(__name__)


class StatusAPIError(Exception):
    pass


class OpenAIStatusMonitor:
    def __init__(self, state: AdminState, store: StateStore, notifier: TelegramNotifier) -> None:
        self.state = state
        self.store = store
        self.notifier = notifier

    async def fetch_incidents(self) -> list[dict[str, Any]]:
        try:
            async with httpx.AsyncClient(timeout=15, follow_redirects=True) as client:
                response = await client.get(settings.OPENAI_STATUS_API_URL)
                response.raise_for_status()
                payload = response.json()
        except (httpx.HTTPError, ValueError, TypeError) as exc:
            raise StatusAPIError(f"OpenAI Status API error: {exc}") from exc

        incidents = payload.get("incidents")
        if not isinstance(incidents, list):
            raise StatusAPIError("OpenAI Status API returned no incidents list")
        return [incident for incident in incidents if isinstance(incident, dict)]

    async def sync(self) -> int:
        if not self.state.is_source_enabled("incidents"):
            self.store.touch_health("openai_status", "disabled")
            return 0

        incidents = await self.fetch_incidents()
        tracked = self.store.tracked_incident_ids()
        synchronized = 0
        for incident in incidents:
            incident_id = str(incident.get("id", ""))
            status = str(incident.get("status", "")).lower()
            if not incident_id:
                continue
            if status == "resolved" and incident_id not in tracked:
                continue
            if await self.notifier.sync_incident(incident):
                synchronized += 1

        self.store.touch_health("openai_status", f"synced={synchronized}")
        return synchronized
