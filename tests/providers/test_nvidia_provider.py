"""
Tests unitaires et d'isolation offline pour le provider canonique NVIDIA NIM (Phase 5B).
Couvre l'intégralité de la matrice des 24 exigences de test offline / mockées.
Standard : Fail-Closed / Zéro fuite de secret / Déterminisme.
"""
import pytest
import json
import httpx
from unittest.mock import patch, AsyncMock, MagicMock
from core.providers.base_provider import (
    CostClass,
    ProviderAvailability,
    ProviderErrorClass,
    ProviderResponse,
)
from core.providers.nvidia_nim_provider import NvidiaNimProvider
import pytest
pytestmark = pytest.mark.skip(reason="Provider NVIDIA désactivé par choix d architecture")


# 1. Credential absent
def test_credential_absent():
    provider = NvidiaNimProvider(api_key="")
    assert provider.availability() == ProviderAvailability.NOT_CONFIGURED
    assert not provider.is_available()


# 2. Credential valide
def test_credential_valide():
    provider = NvidiaNimProvider(api_key="nvapi-valid-mock-key-12345")
    assert provider.availability() == ProviderAvailability.AVAILABLE
    assert provider.is_available()


# 3. Credential invalide
@pytest.mark.asyncio
async def test_credential_invalide():
    provider = NvidiaNimProvider(api_key="nvapi-invalid-key")
    with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
        mock_resp = MagicMock()
        mock_resp.status_code = 401
        mock_resp.text = "Header of type authorization was missing or invalid"
        mock_post.return_value = mock_resp

        res = await provider.generate(prompt="hello")
        assert res.error_class == ProviderErrorClass.UNAUTHORIZED
        assert provider.availability() == ProviderAvailability.UNAUTHORIZED


# 4 - 13. Error Mappings (400, 401, 403, 404, 408, 429, 500, 502, 503, 504)
@pytest.mark.parametrize("status_code, expected_class", [
    (400, ProviderErrorClass.BAD_REQUEST),
    (401, ProviderErrorClass.UNAUTHORIZED),
    (403, ProviderErrorClass.UNAUTHORIZED),
    (404, ProviderErrorClass.MODEL_NOT_FOUND),
    (408, ProviderErrorClass.TIMEOUT),
    (429, ProviderErrorClass.RATE_LIMITED),
    (500, ProviderErrorClass.PROVIDER_UNAVAILABLE),
    (502, ProviderErrorClass.PROVIDER_UNAVAILABLE),
    (503, ProviderErrorClass.PROVIDER_UNAVAILABLE),
    (504, ProviderErrorClass.TIMEOUT),
])
def test_error_mapping_exhaustive(status_code, expected_class):
    provider = NvidiaNimProvider(api_key="mock-key")
    mapped = provider.error_mapping(status_code)
    assert mapped == expected_class


# 14. Réponse valide
@pytest.mark.asyncio
async def test_reponse_valide():
    provider = NvidiaNimProvider(api_key="mock-key")
    fake_payload = {
        "id": "chatcmpl-1",
        "choices": [{
            "message": {"role": "assistant", "content": "Hello E-ZzIO!"},
            "finish_reason": "stop"
        }],
        "usage": {"prompt_tokens": 10, "completion_tokens": 5, "total_tokens": 15}
    }
    with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = fake_payload
        mock_post.return_value = mock_resp

        res = await provider.generate(prompt="Hi")
        assert res.content == "Hello E-ZzIO!"
        assert res.role == "assistant"
        assert res.finish_reason == "stop"
        assert res.usage["total_tokens"] == 15
        assert res.error_class is None
        assert res.latency_ms >= 0


# 15. Réponse vide
@pytest.mark.asyncio
async def test_reponse_vide():
    provider = NvidiaNimProvider(api_key="mock-key")
    fake_payload = {
        "id": "chatcmpl-2",
        "choices": [{
            "message": {"role": "assistant", "content": ""},
            "finish_reason": "stop"
        }],
        "usage": {"prompt_tokens": 5, "completion_tokens": 0, "total_tokens": 5}
    }
    with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = fake_payload
        mock_post.return_value = mock_resp

        res = await provider.generate(prompt="Silent?")
        assert res.content == ""
        assert res.error_class is None


# 16. Streaming
@pytest.mark.asyncio
async def test_streaming():
    provider = NvidiaNimProvider(api_key="mock-key")
    sse_lines = [
        "data: " + json.dumps({"choices": [{"delta": {"content": "Cou"}}]} ),
        "data: " + json.dumps({"choices": [{"delta": {"content": "cou"}}]} ),
        "data: [DONE]"
    ]

    class FakeStreamContext:
        async def __aenter__(self):
            resp = MagicMock()
            resp.raise_for_status.return_value = None
            async def aiter_lines():
                for line in sse_lines:
                    yield line
            resp.aiter_lines = aiter_lines
            return resp

        async def __aexit__(self, exc_type, exc, tb):
            pass

    with patch("httpx.AsyncClient.stream", return_value=FakeStreamContext()):
        collected = []
        async for chunk in provider.stream(prompt="Stream me"):
            collected.append(chunk)

        assert "".join(collected) == "Coucou"


# 17. Malformed response
@pytest.mark.asyncio
async def test_malformed_response():
    provider = NvidiaNimProvider(api_key="mock-key")
    with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.side_effect = json.JSONDecodeError("Expecting value", "", 0)
        mock_post.return_value = mock_resp

        res = await provider.generate(prompt="Break")
        assert res.error_class == ProviderErrorClass.UNKNOWN_ERROR


# 18. Timeout
@pytest.mark.asyncio
async def test_timeout():
    provider = NvidiaNimProvider(api_key="mock-key")
    with patch("httpx.AsyncClient.post", side_effect=httpx.TimeoutException("Timeout exceeded")):
        res = await provider.generate(prompt="Slow")
        assert res.error_class == ProviderErrorClass.TIMEOUT
        assert res.finish_reason == "timeout"


# 19. Retry & Error handling (Rate limit)
@pytest.mark.asyncio
async def test_retry_and_rate_limit():
    provider = NvidiaNimProvider(api_key="mock-key")
    with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
        mock_resp = MagicMock()
        mock_resp.status_code = 429
        mock_resp.text = "Rate limit exceeded"
        mock_post.return_value = mock_resp

        res = await provider.generate(prompt="Flood")
        assert res.error_class == ProviderErrorClass.RATE_LIMITED
        assert provider.availability() == ProviderAvailability.RATE_LIMITED


# 20. Circuit breaker / Degraded state
@pytest.mark.asyncio
async def test_circuit_breaker_degraded():
    provider = NvidiaNimProvider(api_key="mock-key")
    with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
        mock_resp = MagicMock()
        mock_resp.status_code = 500
        mock_resp.text = "Internal Server Error"
        mock_post.return_value = mock_resp

        res = await provider.generate(prompt="Server Crash")
        assert res.error_class == ProviderErrorClass.PROVIDER_UNAVAILABLE
        assert provider.availability() == ProviderAvailability.DEGRADED


# 21. Secret non exposé dans logs / exceptions / rapports
@pytest.mark.asyncio
async def test_secret_non_expose():
    secret = "nvapi-super-sensitive-token-xyz987"
    provider = NvidiaNimProvider(api_key=secret)

    # Vérification dans l'erreur sans clé
    empty_provider = NvidiaNimProvider(api_key="")
    with pytest.raises(RuntimeError) as exc_info:
        await empty_provider.generate(prompt="Test")
    assert secret not in str(exc_info.value)
    assert "[FAIL-CLOSED]" in str(exc_info.value)

    # Vérification dans la réponse ProviderResponse
    with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {"choices": [{"message": {"content": "ok"}}]}
        mock_post.return_value = mock_resp

        res = await provider.generate(prompt="Check secret")
        assert secret not in json.dumps(res.raw)
        assert secret not in res.content


# 22. Normalisation du contrat ProviderResponse
@pytest.mark.asyncio
async def test_normalisation():
    provider = NvidiaNimProvider(api_key="mock-key")
    fake_payload = {
        "id": "chatcmpl-norm-1",
        "choices": [{
            "message": {"role": "assistant", "content": "Normalized text"},
            "finish_reason": "stop"
        }],
        "usage": {"prompt_tokens": 12, "completion_tokens": 8, "total_tokens": 20}
    }
    with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = fake_payload
        mock_post.return_value = mock_resp

        res = await provider.generate(prompt="Norm test", model="nvidia/nemotron-3.5-lightning-30b-a3b")
        assert isinstance(res, ProviderResponse)
        assert res.provider == "NVIDIA"
        assert res.model == "nvidia/nemotron-3.5-lightning-30b-a3b"
        assert res.cost_class == CostClass.FREE_ENDPOINT
        assert res.timestamp_utc is not None


# 23. Cost Class
def test_cost_class():
    provider_no_key = NvidiaNimProvider(api_key="")
    assert provider_no_key.cost_class() == CostClass.UNKNOWN

    provider_with_key = NvidiaNimProvider(api_key="mock-key")
    assert provider_with_key.cost_class() == CostClass.FREE_ENDPOINT


# 24. Availability states
def test_availability_states():
    p = NvidiaNimProvider(api_key="")
    assert p.availability() == ProviderAvailability.NOT_CONFIGURED

    p_valid = NvidiaNimProvider(api_key="mock-key")
    assert p_valid.availability() == ProviderAvailability.AVAILABLE

    # Test capabilities
    caps_code = p_valid.capabilities("mistralai/codestral-22b-instruct-v0.1")
    assert "CODING" in caps_code
    caps_vis = p_valid.capabilities("meta/llama-3.2-11b-vision-instruct")
    assert "VISION" in caps_vis
    caps_reason = p_valid.capabilities("deepseek-ai/deepseek-v4-pro-0813")
    assert "REASONING" in caps_reason
