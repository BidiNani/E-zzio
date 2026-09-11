"""core/bus.py - Bus d'événements asynchrone et persistance SQLite WAL pour E-ZzIO."""

from __future__ import annotations

import asyncio
import json
import sqlite3
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional


@dataclass
class AgentEvent:
    run_id: str
    event_type: str  # "plan", "thought", "tool_call", "terminal", "artifact", "final"
    agent_id: str
    payload: Dict[str, Any]
    requires_approval: bool = False
    event_id: Optional[int] = None
    created_at: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )


class EventBus:
    def __init__(self, db_path: Path | str = "ezzio.db") -> None:
        self.db_path = Path(db_path)
        self._subscribers: Dict[str, List[asyncio.Queue[AgentEvent]]] = {}
        self._init_db()

    def _get_connection(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path, check_same_thread=False)
        conn.execute("PRAGMA journal_mode=WAL;")
        conn.execute("PRAGMA synchronous=NORMAL;")
        conn.execute("PRAGMA busy_timeout=5000;")
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self) -> None:
        with self._get_connection() as conn:
            conn.executescript(
                """
                CREATE TABLE IF NOT EXISTS runs (
                    run_id TEXT PRIMARY KEY,
                    prompt TEXT NOT NULL,
                    profile TEXT NOT NULL,
                    status TEXT NOT NULL,
                    created_at TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS events (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    run_id TEXT NOT NULL,
                    event_type TEXT NOT NULL,
                    agent_id TEXT NOT NULL,
                    payload TEXT NOT NULL,
                    requires_approval INTEGER DEFAULT 0,
                    status TEXT DEFAULT 'emitted',
                    created_at TEXT NOT NULL,
                    FOREIGN KEY(run_id) REFERENCES runs(run_id)
                );
                """
            )

    def register_run(self, run_id: str, prompt: str, profile: str = "normal") -> None:
        now = datetime.now(timezone.utc).isoformat()
        with self._get_connection() as conn:
            conn.execute(
                "INSERT INTO runs (run_id, prompt, profile, status, created_at) VALUES (?, ?, ?, ?, ?)",
                (run_id, prompt, profile, "running", now),
            )

    async def emit(self, event: AgentEvent) -> AgentEvent:
        with self._get_connection() as conn:
            cur = conn.execute(
                """
                INSERT INTO events (run_id, event_type, agent_id, payload, requires_approval, status, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    event.run_id,
                    event.event_type,
                    event.agent_id,
                    json.dumps(event.payload, ensure_ascii=False),
                    1 if event.requires_approval else 0,
                    "waiting_approval" if event.requires_approval else "emitted",
                    event.created_at,
                ),
            )
            event.event_id = cur.lastrowid

        queues = self._subscribers.get(event.run_id, [])
        for q in queues:
            await q.put(event)

        return event

    def subscribe(self, run_id: str) -> asyncio.Queue[AgentEvent]:
        q: asyncio.Queue[AgentEvent] = asyncio.Queue()
        self._subscribers.setdefault(run_id, []).append(q)
        return q

    def unsubscribe(self, run_id: str, q: asyncio.Queue[AgentEvent]) -> None:
        if run_id in self._subscribers and q in self._subscribers[run_id]:
            self._subscribers[run_id].remove(q)
            if not self._subscribers[run_id]:
                del self._subscribers[run_id]

    # Politique de rétention : événements applicatifs = 90 jours.
    # Les runs sont conservés (registre d'audit) sauf purge explicite.
    EVENT_RETENTION_DAYS = 90

    def prune_events_older_than(self, days: int = EVENT_RETENTION_DAYS) -> int:
        """Supprime les événements plus anciens que le seuil (timestamps ISO)."""
        from datetime import timedelta as _td

        cutoff = (datetime.now(timezone.utc) - _td(days=days)).isoformat()
        with self._get_connection() as conn:
            cur = conn.execute("DELETE FROM events WHERE created_at < ?", (cutoff,))
            return cur.rowcount

    def get_run_events(self, run_id: str) -> List[Dict[str, Any]]:
        with self._get_connection() as conn:
            rows = conn.execute(
                "SELECT * FROM events WHERE run_id = ? ORDER BY id ASC", (run_id,)
            ).fetchall()
            return [
                {
                    "id": r["id"],
                    "run_id": r["run_id"],
                    "event_type": r["event_type"],
                    "agent_id": r["agent_id"],
                    "payload": json.loads(r["payload"]),
                    "requires_approval": bool(r["requires_approval"]),
                    "status": r["status"],
                    "created_at": r["created_at"],
                }
                for r in rows
            ]
