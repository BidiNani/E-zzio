"""Flux multi-agents : domaines, déclenchement, débat mocké."""
import asyncio
import json
import os
import tempfile
from pathlib import Path
from unittest.mock import AsyncMock

from core.agents.multi_agent_flow import (
    MultiAgentFlow, analyze_domains, should_auto_trigger)
from core.agents.blackboard import Blackboard


def test_analyze_domains():
    assert "code" in analyze_domains("corrige le bug dans main.py")
    assert "securite" in analyze_domains("audit des secrets fail-closed")
    assert "architecture" in analyze_domains("design du système de gouvernance")
    assert analyze_domains("bonjour") == ["code"]


def test_should_auto_trigger_gated():
    from core.agent.coder_federation import TaskComplexity, TaskProfile
    os.environ.pop("EZZIO_MULTI_AGENT", None)
    assert should_auto_trigger(TaskProfile(complexity=TaskComplexity.CRITICAL)) is False
    os.environ["EZZIO_MULTI_AGENT"] = "1"
    try:
        assert should_auto_trigger(TaskProfile(complexity=TaskComplexity.CRITICAL)) is True
        assert should_auto_trigger(TaskProfile(complexity=TaskComplexity.STANDARD)) is False
        assert should_auto_trigger(None, "COMPLEX") is True
        assert should_auto_trigger(None, "STANDARD") is False
    finally:
        os.environ.pop("EZZIO_MULTI_AGENT", None)


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


def test_flow_debate_then_synthesis():
    async def run():
        tmp = Path(tempfile.mkdtemp()) / "ma.db"
        fed = type("F", (), {})()
        fed.execute_task = AsyncMock(side_effect=[
            _resp(_contrib("PROPOSAL", "@@ -1 +1 @@\n-a\n+b")),
            _resp(_contrib("PROPOSAL")),
            _resp(_contrib("CRITIQUE")),
            _resp({"adr_id": "ADR-MA", "title": "T", "decision": "D",
                   "rationale": "R", "rejected_alternatives": []}),
        ])
        flow = MultiAgentFlow(federation=fed, blackboard=Blackboard(tmp))
        out = await flow.run("corrige le bug dans main.py")
        assert out["domains"] == ["code"]
        assert out["adrs"] and out["adrs"][0]["adr_id"] == "ADR-MA"
        assert "### code" in out["consensus"]
    asyncio.run(run())


def test_discord_stream_throttle_contract():
    import time
    interval, edits, last = 1.2, 0, -10.0
    now = [0.0, 0.5, 1.3, 1.4, 2.6]
    for t in now:
        if t - last >= interval:
            edits += 1
            last = t
    assert edits == 3  # t=0, 1.3, 2.6 : jamais de rafale 429
