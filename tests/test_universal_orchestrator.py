"""Orchestrateur universel : ack immédiat, essaim async, journal WAL."""
import asyncio
import json
import tempfile
from pathlib import Path
from unittest.mock import AsyncMock

from core.agents.universal_orchestrator import MissionJournal, UniversalOrchestrator


def _resp(payload: dict):
    from core.providers.base_provider import CostClass, ProviderResponse
    return ProviderResponse(content=json.dumps(payload), model="mock",
                            provider="mock", cost_class=CostClass.LOCAL)


def _contrib(phase, diff=None):
    d = {"phase": phase, "confidence": 0.8, "summary": f"s-{phase}",
         "identified_risks": [], "blockers": []}
    if diff is not None:
        d["unified_diff"] = diff
    return d


def test_ack_immediate_while_swarm_pending():
    async def run():
        tmp = Path(tempfile.mkdtemp()) / "m.db"
        fed = type("F", (), {})()
        started = asyncio.Event()
        finished = asyncio.Event()

        async def slow_execute(**kwargs):
            started.set()
            await asyncio.sleep(5.0)
            finished.set()
            return _resp(_contrib("PROPOSAL"))

        fed.execute_task = slow_execute
        orch = UniversalOrchestrator(federation=fed,
                                     journal=MissionJournal(tmp))
        import time
        t0 = time.perf_counter()
        ack = await orch.submit_complex("tâche longue", channel="web")
        dt_ms = (time.perf_counter() - t0) * 1000
        assert ack["ok"] is True and ack["status"] == "QUEUED"
        assert dt_ms < 1000, dt_ms  # conversation non bloquée
        assert await asyncio.wait_for(started.wait(), timeout=10)
        assert orch.pending() == [ack["mission_id"]]
        for t in list(orch._tasks.values()):
            t.cancel()
        try:
            await asyncio.gather(*orch._tasks.values(), return_exceptions=True)
        except Exception:
            pass
        hist = await orch.journal.history(ack["mission_id"])
        assert hist and hist[0]["transition"] == "SUBMITTED"

    asyncio.run(run())


def test_swarm_debate_delivers_adr():
    async def run():
        tmp = Path(tempfile.mkdtemp()) / "m2.db"
        fed = type("F", (), {})()
        fed.execute_task = AsyncMock(side_effect=[
            _resp(_contrib("PROPOSAL", "@@ -1 +1 @@\n-a\n+b")),
            _resp(_contrib("PROPOSAL")),
            _resp(_contrib("CRITIQUE")),
            _resp({"adr_id": "ADR-U", "title": "T", "decision": "D",
                   "rationale": "R", "rejected_alternatives": []}),
        ])
        orch = UniversalOrchestrator(federation=fed,
                                     journal=MissionJournal(tmp))
        out = await orch._run_swarm("m-test", "corrige le bug", "", "web", "")
        assert out["ok"] is True
        assert out["result"]["adrs"][0]["adr_id"] == "ADR-U"
        hist = await orch.journal.history("m-test")
        transitions = [h["transition"] for h in hist]
        assert transitions[0] == "DEBATE_START"
        assert transitions[-1] == "DELIVERED"
    asyncio.run(run())


def test_journal_wal_durable():
    async def run():
        import sqlite3
        tmp = Path(tempfile.mkdtemp()) / "m3.db"
        j = MissionJournal(tmp)
        await j.init()
        await j.record("m1", "SUBMITTED", "QUEUED", "goal")
        mode = sqlite3.connect(str(tmp)).execute("PRAGMA journal_mode").fetchone()[0]
        assert mode.lower() == "wal"
        assert (await j.history("m1"))[0]["status"] == "QUEUED"
    asyncio.run(run())
