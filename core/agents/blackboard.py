"""E-ZZIO — Blackboard partagé (SQLite WAL + FTS5)."""
from __future__ import annotations

import json
import time
import uuid
from pathlib import Path
from typing import List, Optional

import aiosqlite

from core.agents.schemas import ADRRecord, AgentContribution

DEFAULT_DB = Path("G:/AI/E-zzio/runtime/evidence/blackboard.db")

_PRAGMAS = [
    "PRAGMA journal_mode = WAL;",
    "PRAGMA synchronous = NORMAL;",
    "PRAGMA cache_size = -64000;",
    "PRAGMA mmap_size = 268435456;",
    "PRAGMA temp_store = MEMORY;",
]

_SCHEMA = """
CREATE TABLE IF NOT EXISTS blackboard_sessions (
    id TEXT PRIMARY KEY, goal TEXT NOT NULL, status TEXT NOT NULL, created_at REAL NOT NULL);
CREATE TABLE IF NOT EXISTS blackboard_contributions (
    id TEXT PRIMARY KEY, session_id TEXT NOT NULL, round INTEGER NOT NULL,
    agent_id TEXT NOT NULL, phase TEXT NOT NULL, payload_json TEXT NOT NULL,
    created_at REAL NOT NULL);
CREATE INDEX IF NOT EXISTS idx_contrib_session_round
    ON blackboard_contributions(session_id, round);
CREATE TABLE IF NOT EXISTS architecture_decisions (
    id TEXT PRIMARY KEY, title TEXT NOT NULL, decision TEXT NOT NULL,
    rationale TEXT NOT NULL, created_at REAL NOT NULL);
CREATE VIRTUAL TABLE IF NOT EXISTS adr_fts USING fts5(
    title, decision, rationale, content='architecture_decisions', content_rowid='rowid');
CREATE TRIGGER IF NOT EXISTS adr_ai AFTER INSERT ON architecture_decisions BEGIN
    INSERT INTO adr_fts(rowid, title, decision, rationale)
    VALUES (new.rowid, new.title, new.decision, new.rationale);
END;
"""


class Blackboard:
    def __init__(self, db_path: Path | str = DEFAULT_DB):
        self.db_path = Path(db_path)

    async def init(self) -> None:
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        async with aiosqlite.connect(self.db_path) as db:
            for pr in _PRAGMAS:
                await db.execute(pr)
            await db.executescript(_SCHEMA)
            await db.commit()

    async def create_session(self, goal: str) -> str:
        sid = f"sess_{uuid.uuid4().hex[:10]}"
        async with aiosqlite.connect(self.db_path) as db:
            for pr in _PRAGMAS:
                await db.execute(pr)
            await db.execute(
                "INSERT INTO blackboard_sessions (id, goal, status, created_at) VALUES (?,?,?,?);",
                (sid, goal, "OPEN", time.time()),
            )
            await db.commit()
        return sid

    async def post_contribution(
        self, session_id: str, round_num: int, contribution: AgentContribution
    ) -> str:
        cid = f"contrib_{uuid.uuid4().hex[:10]}"
        async with aiosqlite.connect(self.db_path) as db:
            for pr in _PRAGMAS:
                await db.execute(pr)
            await db.execute(
                "INSERT INTO blackboard_contributions "
                "(id, session_id, round, agent_id, phase, payload_json, created_at) "
                "VALUES (?,?,?,?,?,?,?);",
                (cid, session_id, round_num, contribution.agent_id,
                 contribution.phase, contribution.model_dump_json(), time.time()),
            )
            await db.commit()
        return cid

    async def get_round_state(self, session_id: str, round_num: int) -> List[AgentContribution]:
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            cur = await db.execute(
                "SELECT payload_json FROM blackboard_contributions "
                "WHERE session_id = ? AND round = ? ORDER BY created_at;",
                (session_id, round_num),
            )
            rows = await cur.fetchall()
        return [AgentContribution.model_validate_json(r["payload_json"]) for r in rows]

    async def record_adr(self, adr: ADRRecord) -> str:
        async with aiosqlite.connect(self.db_path) as db:
            for pr in _PRAGMAS:
                await db.execute(pr)
            await db.execute(
                "INSERT INTO architecture_decisions (id, title, decision, rationale, created_at) "
                "VALUES (?,?,?,?,?);",
                (adr.adr_id, adr.title, adr.decision, adr.rationale, time.time()),
            )
            await db.commit()
        return adr.adr_id

    async def find_similar_adr(self, query: str, limit: int = 3) -> List[dict]:
        """FTS5 : évite de re-délibérer un problème déjà tranché."""
        import re as _re
        safe = " ".join(_re.findall(r"[A-Za-zÀ-ÿ0-9_]+", query or ""))[:200]
        if not safe:
            return []
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            try:
                cur = await db.execute(
                    "SELECT d.id, d.title, d.decision FROM architecture_decisions d "
                    "JOIN adr_fts f ON f.rowid = d.rowid "
                    "WHERE adr_fts MATCH ? LIMIT ?;",
                    (safe, limit),
                )
                return [dict(r) for r in await cur.fetchall()]
            except Exception:
                cur = await db.execute(
                    "SELECT id, title, decision FROM architecture_decisions "
                    "WHERE title LIKE ? OR decision LIKE ? LIMIT ?;",
                    (f"%{safe[:40]}%", f"%{safe[:40]}%", limit),
                )
                return [dict(r) for r in await cur.fetchall()]

    async def close_session(self, session_id: str, status: str = "CLOSED") -> None:
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                "UPDATE blackboard_sessions SET status = ? WHERE id = ?;",
                (status, session_id),
            )
            await db.commit()
