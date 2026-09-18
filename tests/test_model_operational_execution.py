import os
from unittest.mock import AsyncMock, patch

import pytest

from core.decision_router import DecisionRouter, SearchMode
from core.providers.gemini_provider import GeminiProvider
from core.providers.ollama_provider import OllamaProvider


@pytest.mark.asyncio
async def test_model_router_operational_multi_provider_routing():
    p_ollama = OllamaProvider()
    p_gemini = GeminiProvider(api_key="mock_key")

    router = DecisionRouter([p_ollama, p_gemini])
    assert any(p.name == "ollama" for p in router.providers)
    assert any(p.name == "gemini" for p in router.providers)

    # Test route locale vers Ollama
    with patch.object(p_ollama, "search", new_callable=AsyncMock) as mock_o:
        mock_o.return_value = {
            "provider": "ollama",
            "model": "gpt-oss-20b",
            "data": {"text": "Réponse locale Ollama"}
        }
        res_loc = await router.search("Question locale", mode=SearchMode.LOCAL)
        assert res_loc["provider"] == "ollama"
        assert res_loc["data"]["text"] == "Réponse locale Ollama"

    # Test route Cloud vers Gemini
    with patch.object(p_gemini, "search", new_callable=AsyncMock) as mock_g:
        mock_g.return_value = {
            "provider": "gemini",
            "model": "gemini-3.7-flash",
            "data": {"text": "Réponse Cloud Gemini"}
        }
        res_cloud = await router.search("Question cloud", mode=SearchMode.GOOGLE)
        assert res_cloud["provider"] == "gemini"
        assert res_cloud["data"]["text"] == "Réponse Cloud Gemini"
