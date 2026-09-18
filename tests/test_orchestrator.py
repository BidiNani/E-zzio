"""tests/test_orchestrator.py - Validation d'intégration de bout en bout de l'orchestrateur."""

from pathlib import Path

import httpx
import pytest

from core.bus import EventBus
from core.cognitive_router import ModelRouter
from core.orchestrator import Orchestrator
from core.sandbox import SecuritySandbox


def mock_network(request: httpx.Request) -> httpx.Response:
    if "/api/generate" in str(request.url):
        return httpx.Response(200, json={"response": "Résolution locale Ollama exécutée."})
    return httpx.Response(404)


@pytest.mark.asyncio
async def test_orchestrator_complete_cycle(tmp_path: Path) -> None:
    bus = EventBus(db_path=tmp_path / "orch_test.db")
    transport = httpx.MockTransport(mock_network)
    async with httpx.AsyncClient(transport=transport) as client:
        router = ModelRouter(gemini_api_key=None, http_client=client)
        sandbox = SecuritySandbox(workspace_root=tmp_path)
        orchestrator = Orchestrator(bus=bus, router=router, sandbox=sandbox)

        run_id = "run_full_001"
        bus.register_run(run_id, prompt="Corriger le code", profile="prive")

        res = await orchestrator.run(run_id=run_id, prompt="Corriger le code", profile="prive")

        assert res["status"] == "completed"
        assert res["provider"] == "ollama"
        assert "Résolution locale" in res["text"]

        events = bus.get_run_events(run_id)
        event_types = [e["event_type"] for e in events]
        assert "plan" in event_types
        assert "thought" in event_types
        assert "final" in event_types


@pytest.mark.asyncio
async def test_orchestrator_with_tool_command(tmp_path: Path) -> None:
    bus = EventBus(db_path=tmp_path / "orch_tool.db")
    transport = httpx.MockTransport(mock_network)
    async with httpx.AsyncClient(transport=transport) as client:
        router = ModelRouter(gemini_api_key=None, http_client=client)
        sandbox = SecuritySandbox(workspace_root=tmp_path)
        orchestrator = Orchestrator(bus=bus, router=router, sandbox=sandbox)

        run_id = "run_tool_002"
        bus.register_run(run_id, prompt="exec: echo ezzio-terminal-test")

        res = await orchestrator.run(run_id=run_id, prompt="exec: echo ezzio-terminal-test")

        assert res["status"] == "completed"
        assert res["execution"] is not None
        assert res["execution"]["exit_code"] == 0
        assert "ezzio-terminal-test" in res["execution"]["stdout"]

        events = bus.get_run_events(run_id)
        event_types = [e["event_type"] for e in events]
        assert "tool_call" in event_types
        assert "terminal" in event_types
