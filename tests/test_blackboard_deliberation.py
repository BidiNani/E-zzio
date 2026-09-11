"""Délibération 2 tours : blackboard SQLite + ADR (fédération mockée)."""
import asyncio
import json
import tempfile
from pathlib import Path
from unittest.mock import AsyncMock

from core.agents.blackboard import Blackboard
from core.agents.orchestrator import DeliberationOrchestrator
from core.providers.base_provider import CostClass, ProviderResponse


def _resp(payload: dict) -> ProviderResponse:
    return ProviderResponse(content=json.dumps(payload), model="mock",
                            provider="mock", cost_class=CostClass.LOCAL)


def _contrib(phase, diff=None):
    d = {"phase": phase, "confidence": 0.8, "summary": f"s-{phase}",
         "identified_risks": [], "blockers": []}
    if diff is not None:
        d["unified_diff"] = diff
    return d


def test_two_round_deliberation_with_adr():
    async def run():
        tmp = Path(tempfile.mkdtemp()) / "bb.db"
        fed = type("F", (), {})()
        fed.execute_task = AsyncMock(side_effect=[
            _resp(_contrib("PROPOSAL", "@@ -1 +1 @@\n-a\n+b")),
            _resp(_contrib("PROPOSAL")),
            _resp(_contrib("CRITIQUE")),
            _resp({"adr_id": "ADR-7", "title": "Choix B",
                   "decision": "Appliquer B.", "rationale": "Moins de risque.",
                   "rejected_alternatives": ["A"]}),
        ])
        orch = DeliberationOrchestrator(federation=fed,
                                        blackboard=Blackboard(tmp))
        adr = await orch.deliberate("Choisir A ou B", "def f(): ...")
        assert adr.adr_id == "ADR-7" and adr.status == "PROPOSED"
        return adr

    adr = asyncio.run(run())
    assert adr.title == "Choix B"


def test_round_state_persisted():
    async def run():
        from core.agents.schemas import AgentContribution
        tmp = Path(tempfile.mkdtemp()) / "bb2.db"
        board = Blackboard(tmp)
        await board.init()
        sid = await board.create_session("goal")
        await board.post_contribution(
            sid, 1, AgentContribution(agent_id="coder", phase="PROPOSAL",
                                      confidence=0.7, summary="s"))
        got = await board.get_round_state(sid, 1)
        assert len(got) == 1 and got[0].agent_id == "coder"
        sims = await board.find_similar_adr("goal")
        assert isinstance(sims, list)
    asyncio.run(run())
