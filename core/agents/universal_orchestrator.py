"""E-ZZIO — orchestrateur universel : ack immédiat + essaim async + journal WAL.

- Conversation principale jamais bloquée (asyncio.create_task).
- Débat : MultiAgentFlow (Code/Qualité/Architecte, cap 2 tours, ADR).
- Auto-correction : SelfHealingLoop sec (diagnostic, cap 3, 0 écriture
  sans apply=True explicite).
- Journal durable append-only SQLite WAL : historique des transitions
  (observabilité/reprise UNKNOWN, JAMAIS de RECOVERED auto).
- Diffusion : AgentTracer (SSE/Discord/OpenAI existants, 0 second bus).
"""
from __future__ import annotations

import asyncio
import logging
import time
import uuid
from pathlib import Path
from typing import Any, Dict, Optional

import aiosqlite

logger = logging.getLogger("ezzio.universal_orchestrator")

DEFAULT_DB = Path("G:/AI/E-zzio/runtime/evidence/missions.db")

_PRAGMAS = [
    "PRAGMA journal_mode = WAL;",
    "PRAGMA synchronous = NORMAL;",
    "PRAGMA cache_size = -64000;",
    "PRAGMA mmap_size = 268435456;",
    "PRAGMA temp_store = MEMORY;",
]

_SCHEMA = """
CREATE TABLE IF NOT EXISTS mission_events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    mission_id TEXT NOT NULL, transition TEXT NOT NULL,
    status TEXT NOT NULL, detail TEXT DEFAULT '',
    created_at REAL NOT NULL);
CREATE INDEX IF NOT EXISTS idx_mission_events_mid ON mission_events(mission_id);
"""


class MissionJournal:
    """Journal append-only (jamais de mutation d'état passé)."""

    def __init__(self, db_path: Path | str = DEFAULT_DB):
        self.db_path = Path(db_path)

    async def init(self) -> None:
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        async with aiosqlite.connect(self.db_path) as db:
            for pr in _PRAGMAS:
                await db.execute(pr)
            await db.executescript(_SCHEMA)
            await db.commit()

    async def record(self, mission_id: str, transition: str,
                     status: str, detail: str = "") -> None:
        async with aiosqlite.connect(self.db_path) as db:
            for pr in _PRAGMAS:
                await db.execute(pr)
            await db.execute(
                "INSERT INTO mission_events (mission_id, transition, status, detail, created_at)"
                " VALUES (?,?,?,?,?);",
                (mission_id, transition, status, detail[:2000], time.time()),
            )
            await db.commit()

    async def history(self, mission_id: str, limit: int = 100) -> list:
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            cur = await db.execute(
                "SELECT transition, status, detail, created_at FROM mission_events"
                " WHERE mission_id = ? ORDER BY id LIMIT ?;",
                (mission_id, limit),
            )
            return [dict(r) for r in await cur.fetchall()]


class UniversalOrchestrator:
    """Soumission complexe : ack immédiat, essaim en fond, journal WAL."""

    def __init__(self, federation=None, journal: Optional[MissionJournal] = None):
        self.federation = federation
        self.journal = journal or MissionJournal()
        self._tasks: Dict[str, asyncio.Task] = {}

    async def submit_complex(self, request: str, skeleton: str = "",
                             channel: str = "web",
                             session_id: str = "") -> Dict[str, Any]:
        """Retourne l'accusé SANS attendre l'essaim (non-interférence)."""
        from core.telemetry.agent_tracer import tracer
        mission_id = f"uma_{uuid.uuid4().hex[:10]}"
        await self.journal.init()
        await self.journal.record(mission_id, "SUBMITTED", "QUEUED", request[:300])
        tracer.lifecycle("START", "RUNNING", agent_id="universal_orchestrator",
                         trace_id=mission_id, payload={"goal": request[:300]})
        task = asyncio.create_task(
            self._run_swarm(mission_id, request, skeleton, channel, session_id))
        self._tasks[mission_id] = task
        task.add_done_callback(lambda _t: self._tasks.pop(mission_id, None))
        return {"ok": True, "mission_id": mission_id, "status": "QUEUED",
                "ack": "Essaim en cours, conversation disponible."}

    async def _run_swarm(self, mission_id: str, request: str, skeleton: str,
                         channel: str, session_id: str) -> Dict[str, Any]:
        from core.telemetry.agent_tracer import tracer
        from core.agents.multi_agent_flow import MultiAgentFlow
        try:
            await self.journal.init()
            await self.journal.record(mission_id, "DEBATE_START", "RUNNING")
            tracer.lifecycle("STATUS_CHANGE", "RUNNING",
                             agent_id="universal_orchestrator",
                             trace_id=mission_id,
                             payload={"phase": "debate"})
            flow = MultiAgentFlow(federation=self.federation)
            out = await flow.run(request, skeleton)
            # Auto-correction sèche sur échec signalé (cap 3, 0 écriture).
            if any("FAILED" in str(a.get("decision", "")).upper()
                   for a in out.get("adrs", [])):
                from core.orchestration.self_healing_loop import SelfHealingLoop
                heal = SelfHealingLoop(max_retries=3).heal(apply=False)
                await self.journal.record(
                    mission_id, "HEAL_PROBE", "SUCCESS",
                    f"attempts={heal.attempts} fixed={heal.fixed}")
            await self.journal.record(mission_id, "DELIVERED", "SUCCESS",
                                      str(out.get("consensus", ""))[:500])
            tracer.lifecycle("FINISH", "SUCCESS",
                             agent_id="universal_orchestrator",
                             trace_id=mission_id)
            return {"ok": True, "mission_id": mission_id, "result": out}
        except Exception as exc:
            logger.error("[UNIVERSAL] essaim %s en échec : %s", mission_id, exc)
            await self.journal.record(mission_id, "FAILED", "FAILED", str(exc)[:500])
            tracer.lifecycle("ERROR", "FAILED",
                             agent_id="universal_orchestrator",
                             trace_id=mission_id,
                             payload={"error": str(exc)[:500]})
            return {"ok": False, "mission_id": mission_id, "error": str(exc)}

    def pending(self) -> list:
        return [mid for mid, t in self._tasks.items() if not t.done()]
