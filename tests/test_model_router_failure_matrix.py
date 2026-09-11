import pytest
import asyncio
import httpx
from unittest.mock import AsyncMock, patch, MagicMock
from core.decision_router import DecisionRouter, SearchMode
from core.providers.ollama_provider import OllamaProvider
from core.providers.gemini_provider import GeminiProvider

@pytest.mark.asyncio
async def test_ollama_failure_matrix_connection_error_and_timeout():
    # Simulation d'échec réseau / timeout Ollama
    with patch("httpx.AsyncClient.stream", side_effect=httpx.ConnectError("Ollama unreachable")):
        provider = OllamaProvider(base_url="http://127.0.0.1:11434")
        with pytest.raises(httpx.ConnectError):
            await provider.search("prompt test")

@pytest.mark.asyncio
async def test_ollama_empty_response_fallback_data():
    # Réponse où aucun token n'est généré
    class MockStream:
        async def __aenter__(self):
            return self
        async def __aexit__(self, *args):
            pass
        def raise_for_status(self):
            pass
        async def aiter_lines(self):
            yield '{"response": "", "done": true}'

    def mock_stream(*args, **kwargs):
        return MockStream()

    with patch("httpx.AsyncClient.stream", side_effect=mock_stream):
        provider = OllamaProvider(base_url="http://127.0.0.1:11434")
        res = await provider.search("prompt test")
        assert res["provider"] == "ollama"
        assert "Réponse tronquée" in res["data"]["text"]

@pytest.mark.asyncio
async def test_gemini_failure_matrix_auth_error_and_rate_limit():
    # 1. Absence de clé API
    with patch("core.providers.gemini_provider.os.getenv", return_value=None):
        with patch.object(GeminiProvider, "__init__", lambda self: setattr(self, "api_key", None)):
            p = GeminiProvider()
            with pytest.raises(RuntimeError) as exc:
                await p.search("prompt")
            assert "GEMINI_API_KEY manquante" in str(exc.value)

@pytest.mark.asyncio
async def test_decision_router_full_matrix_failover():
    # Simulation d'une cascade: Ollama KO -> Gemini KO -> levée d'erreur explicite
    p_ollama = OllamaProvider()
    p_gemini = GeminiProvider(api_key="mock_key")
    
    with patch.object(p_ollama, "search", side_effect=httpx.ConnectError("Ollama down")), \
         patch.object(p_gemini, "search", side_effect=httpx.HTTPStatusError("429 Rate limit", request=MagicMock(), response=MagicMock(status_code=429))):
        
        router = DecisionRouter([p_ollama, p_gemini])
        with pytest.raises(RuntimeError) as exc:
            await router.search("requête", mode=SearchMode.LOCAL)
        
        err_msg = str(exc.value)
        assert "Échec de recherche" in err_msg
        assert "ConnectError" in err_msg
