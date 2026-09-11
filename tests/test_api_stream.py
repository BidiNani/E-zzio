"""tests/test_api_stream.py - Validation du streaming SSE et de l'orchestration en arrière-plan."""

import json
from pathlib import Path
import httpx
import pytest
from core.api import create_app
from core.bus import EventBus
from core.cognitive_router import ModelRouter
from core.sandbox import SecuritySandbox

try:
    from httpx import ASGITransport, AsyncClient

    def get_client(app):
        return AsyncClient(transport=ASGITransport(app=app), base_url="http://test")
except (ImportError, TypeError):
    from httpx import AsyncClient

    def get_client(app):
        return AsyncClient(app=app, base_url="http://test")


def mock_network(request: httpx.Request) -> httpx.Response:
    if "/api/generate" in str(request.url):
        return httpx.Response(200, json={"response": "Réponse streaming validée issue d'Ollama."})
    return httpx.Response(404)


@pytest.mark.asyncio
async def test_create_run_and_stream(tmp_path: Path) -> None:
    bus = EventBus(db_path=tmp_path / "test_api.db")
    transport = httpx.MockTransport(mock_network)
    async with httpx.AsyncClient(transport=transport) as mock_http:
        router = ModelRouter(gemini_api_key=None, http_client=mock_http)
        sandbox = SecuritySandbox(workspace_root=tmp_path)
        app = create_app(bus=bus, router=router, sandbox=sandbox)

        async with get_client(app) as client:
            res = await client.post(
                "/api/runs",
                json={"prompt": "Vérifier le statut SSE", "profile": "prive"},
            )
            assert res.status_code == 200
            run_id = res.json()["run_id"]

            # Consommation du flux SSE diffusé en temps réel par l'orchestrateur
            received_events = []
            async with client.stream("GET", f"/api/runs/{run_id}/stream") as stream:
                async for line in stream.aiter_lines():
                    if line.startswith("data: "):
                        payload = json.loads(line.removeprefix("data: "))
                        received_events.append(payload)
                        if payload.get("event_type") == "final":
                            break

            event_types = [e["event_type"] for e in received_events]
            assert "plan" in event_types
            assert "thought" in event_types
            assert "final" in event_types
            assert any("Ollama" in e.get("payload", {}).get("text", "") for e in received_events if e["event_type"] == "final")
