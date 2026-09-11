"""tests/test_model_router.py - Validation du routage cognitif et de la bascule de secours."""

import httpx
import pytest
from core.cognitive_router import ModelRouter


def mock_network_handler(request: httpx.Request) -> httpx.Response:
    url = str(request.url)
    if "generativelanguage.googleapis.com" in url:
        return httpx.Response(503, json={"error": {"message": "Quota exceeded or offline"}})
    if "/api/generate" in url:
        return httpx.Response(200, json={"response": "Réponse locale sécurisée issue d'Ollama."})
    return httpx.Response(404)


@pytest.mark.asyncio
async def test_router_prive_remains_strictly_local() -> None:
    transport = httpx.MockTransport(mock_network_handler)
    async with httpx.AsyncClient(transport=transport) as client:
        router = ModelRouter(gemini_api_key="fake_key", http_client=client)
        routes = router.resolve_route("prive")

        assert routes["primary"]["provider"] == "ollama"
        assert routes["fallback"]["provider"] == "ollama"

        res = await router.complete(profile="prive", prompt="Donnée confidentielle")
        assert res["fallback_triggered"] is False
        assert res["provider_used"] == "ollama"
        assert res["model_used"] == "qwen2.5-coder:7b-instruct-q4_K_M"


@pytest.mark.asyncio
async def test_router_triggers_fallback_on_gemini_outage() -> None:
    transport = httpx.MockTransport(mock_network_handler)
    async with httpx.AsyncClient(transport=transport) as client:
        router = ModelRouter(gemini_api_key="fake_key", http_client=client)

        res = await router.complete(profile="raisonnement", prompt="Refactorisation complexe")
        assert res["fallback_triggered"] is True
        assert res["provider_used"] == "ollama"
        assert res["model_used"] == "phi4-mini:latest"
