"""Télémétrie agents : arbre parent/enfant, SSE, throttle Discord."""
import asyncio
import json

import pytest

from core.telemetry.agent_tracer import AgentTracer, TraceEvent, traced


def _ev(agent="a", parent=None, et="START", st="RUNNING", tool=None):
    return TraceEvent(trace_id="t1", agent_id=agent, parent_id=parent,
                      event_type=et, status=st, tool_name=tool)


def test_parent_child_serialization():
    assert AgentTracer() is AgentTracer()
    parent = _ev(agent="strategic_master")
    child = _ev(agent="coder_subagent", parent="strategic_master",
                et="TOOL_CALL", tool="parse_ast")
    assert child.parent_id == "strategic_master"
    assert child.tool_name == "parse_ast"
    d = json.loads(child.model_dump_json())
    assert d["trace_id"] == "t1" and d["status"] == "RUNNING"
    bad = {"trace_id": "t", "agent_id": "a", "event_type": "NOPE",
           "status": "RUNNING"}
    with pytest.raises(Exception):
        TraceEvent(**bad)


def test_traced_decorator_sync():
    from core.telemetry.agent_tracer import tracer

    async def run():
        q = tracer.subscribe("t-dec")
        collected = []

        @traced("unit_agent")
        def _work():
            return {"success": True}

        async def drain():
            import asyncio as _a
            for _ in range(4):
                try:
                    collected.append(await _a.wait_for(q.get(), timeout=0.5))
                except Exception:
                    break

        with tracer.trace_context("t-dec", "unit_agent"):
            out = _work()
        assert out == {"success": True}
        await drain()
        tracer.unsubscribe(q)
        kinds = [e.event_type for e in collected if e.trace_id == "t-dec"]
        assert "START" in kinds and "FINISH" in kinds

    asyncio.run(run())


def test_tool_choke_emits_without_breaking():
    import tempfile

    from core.agent.tools_registry import ToolRegistry
    reg = ToolRegistry(workspace_root=tempfile.mkdtemp())
    out = reg.execute("nonexistent_tool_xyz", {})
    assert isinstance(out, str)


def test_sse_stream_and_agent_view():
    from fastapi.testclient import TestClient

    from web_server import app
    c = TestClient(app)
    r = c.get("/agent-view")
    assert r.status_code == 200
    assert "Agent View" in r.text and "EventSource" in r.text


def test_discord_throttle_no_429():
    import time

    from core.integrations.discord.cogs.agent_view_cog import AgentViewTracker, render_ascii_tree

    sent, edits = [], []

    async def fake_send(text):
        sent.append(text)
        return "MSG"

    async def fake_edit(msg, text):
        edits.append((msg, text))

    async def run():
        tr = AgentViewTracker(fake_send, fake_edit)
        for i in range(10):
            tr.ingest(_ev(agent=f"ag{i % 2}", et="TOOL_RESULT", st="SUCCESS",
                           tool=f"tool{i}"))
            await tr.maybe_flush()
        await tr.maybe_flush(force=True)
        return tr

    tr = asyncio.run(run())
    # 10 ingestions + flush forcé : ≤ 3 éditions (1Hz), jamais de 429
    assert tr.edits_sent <= 3, tr.edits_sent
    assert len(sent) == 1
    tree = render_ascii_tree("🤖 Orchestrateur [SUCCESS] (1.4s)", [
        {"agent_id": "architecte", "status": "SUCCESS", "tools": [
            {"name": "parse_ast", "duration_ms": 42}]}])
    assert "parse_ast" in tree and "42ms" in tree
