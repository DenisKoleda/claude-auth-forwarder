"""Persistent delivery, incident and health state."""

from __future__ import annotations

import os
import sqlite3
import threading
import time
from pathlib import Path
from typing import Any


class StateStore:
    def __init__(self, path: str) -> None:
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        if not self.path.exists():
            descriptor = os.open(self.path, os.O_WRONLY | os.O_CREAT, 0o600)
            os.close(descriptor)
        os.chmod(self.path, 0o600)
        self._lock = threading.RLock()
        self._connection = sqlite3.connect(self.path, check_same_thread=False)
        self._connection.row_factory = sqlite3.Row
        self._initialize()

    def _initialize(self) -> None:
        with self._lock, self._connection:
            self._connection.executescript(
                """
                CREATE TABLE IF NOT EXISTS deliveries (
                    source_id TEXT NOT NULL,
                    recipient_id INTEGER NOT NULL,
                    delivered INTEGER NOT NULL DEFAULT 0,
                    telegram_message_id INTEGER,
                    attempts INTEGER NOT NULL DEFAULT 0,
                    last_error TEXT,
                    updated_at REAL NOT NULL,
                    PRIMARY KEY (source_id, recipient_id)
                );
                CREATE TABLE IF NOT EXISTS incidents (
                    incident_id TEXT NOT NULL,
                    recipient_id INTEGER NOT NULL,
                    telegram_message_id INTEGER NOT NULL,
                    last_update_id TEXT NOT NULL,
                    status TEXT NOT NULL,
                    updated_at REAL NOT NULL,
                    PRIMARY KEY (incident_id, recipient_id)
                );
                CREATE TABLE IF NOT EXISTS health (
                    name TEXT PRIMARY KEY,
                    timestamp REAL NOT NULL,
                    detail TEXT
                );
                """
            )

    def delivered_recipients(self, source_id: str) -> set[int]:
        with self._lock:
            rows = self._connection.execute(
                "SELECT recipient_id FROM deliveries WHERE source_id = ? AND delivered = 1",
                (source_id,),
            ).fetchall()
        return {int(row["recipient_id"]) for row in rows}

    def record_delivery(
        self,
        source_id: str,
        recipient_id: int,
        delivered: bool,
        message_id: int | None = None,
        error: str | None = None,
    ) -> None:
        with self._lock, self._connection:
            self._connection.execute(
                """
                INSERT INTO deliveries (
                    source_id, recipient_id, delivered, telegram_message_id,
                    attempts, last_error, updated_at
                ) VALUES (?, ?, ?, ?, 1, ?, ?)
                ON CONFLICT(source_id, recipient_id) DO UPDATE SET
                    delivered = excluded.delivered,
                    telegram_message_id = COALESCE(
                        excluded.telegram_message_id, deliveries.telegram_message_id
                    ),
                    attempts = deliveries.attempts + 1,
                    last_error = excluded.last_error,
                    updated_at = excluded.updated_at
                """,
                (
                    source_id,
                    recipient_id,
                    int(delivered),
                    message_id,
                    error,
                    time.time(),
                ),
            )

    def get_incident_message(self, incident_id: str, recipient_id: int) -> dict[str, Any] | None:
        with self._lock:
            row = self._connection.execute(
                "SELECT * FROM incidents WHERE incident_id = ? AND recipient_id = ?",
                (incident_id, recipient_id),
            ).fetchone()
        return dict(row) if row else None

    def record_incident_message(
        self,
        incident_id: str,
        recipient_id: int,
        message_id: int,
        update_id: str,
        status: str,
    ) -> None:
        with self._lock, self._connection:
            self._connection.execute(
                """
                INSERT INTO incidents (
                    incident_id, recipient_id, telegram_message_id,
                    last_update_id, status, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?)
                ON CONFLICT(incident_id, recipient_id) DO UPDATE SET
                    telegram_message_id = excluded.telegram_message_id,
                    last_update_id = excluded.last_update_id,
                    status = excluded.status,
                    updated_at = excluded.updated_at
                """,
                (incident_id, recipient_id, message_id, update_id, status, time.time()),
            )

    def tracked_incident_ids(self) -> set[str]:
        with self._lock:
            rows = self._connection.execute("SELECT DISTINCT incident_id FROM incidents").fetchall()
        return {str(row["incident_id"]) for row in rows}

    def touch_health(self, name: str, detail: str = "") -> None:
        with self._lock, self._connection:
            self._connection.execute(
                """
                INSERT INTO health (name, timestamp, detail) VALUES (?, ?, ?)
                ON CONFLICT(name) DO UPDATE SET
                    timestamp = excluded.timestamp,
                    detail = excluded.detail
                """,
                (name, time.time(), detail[:500]),
            )

    def health_snapshot(self) -> dict[str, dict[str, Any]]:
        with self._lock:
            rows = self._connection.execute("SELECT name, timestamp, detail FROM health").fetchall()
        return {
            str(row["name"]): {
                "timestamp": float(row["timestamp"]),
                "detail": str(row["detail"] or ""),
            }
            for row in rows
        }

    def close(self) -> None:
        with self._lock:
            self._connection.close()
