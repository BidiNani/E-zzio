import json
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

from core.cognition.providers.key_pool import SovereignKeyPool
from core.providers.base_provider import (
    BaseProvider,
    CostClass,
    ProviderAvailability,
    ProviderErrorClass,
    ProviderResponse,
)
from core.providers.groq_provider import GroqProvider


def test_groq_provider_structure():
    provider = GroqProvider(api_key="gsk-mock-key")
    assert provider.name == "groq"
    assert "groq.com" in provider.base_url
    assert isinstance(provider, BaseProvider)


def test_groq_availability_configured():
    provider = GroqProvider(api_key="gsk-mock-key")
    assert provider.availability() == ProviderAvailability.AVAILABLE
    assert provider.is_available() is True


def test_groq_availability_not_configured():
    provider = GroqProvider(key_pool=SovereignKeyPool("groq", []))
    assert provider.availability() == ProviderAvailability.NOT_CONFIGURED
    assert provider.is_available() is False


def test_groq_cost_class():
    provider = GroqProvider(api_key="gsk-mock-key")
    assert provider.cost_class() == CostClass.FREE_ENDPOINT


def test_groq_capabilities():
    provider = GroqProvider(api_key="gsk-mock-key")
    caps = provider.capabilities()
    assert "TEXT" in caps
    assert "CODING" in caps
    assert "FAST_INFERENCE" in caps


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
def test_groq_error_mapping(status_code, expected_class):
    provider = GroqProvider(api_key="gsk-mock-key")
    assert provider.error_mapping(status_code) == expected_class


@pytest.mark.asyncio
async def test_groq_health_healthy():
    provider = GroqProvider(api_key="gsk-mock-key")
    with patch("httpx.AsyncClient.get", new_callable=AsyncMock) as mock_get:
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {"data": [{"id": "llama-3.3-70b-versatile"}]}
        mock_get.return_value = mock_resp

        health = await provider.health()
        assert health["status"] == "healthy"
        assert health["online"] is True
        assert "llama-3.3-70b-versatile" in health["models"]


@pytest.mark.asyncio
async def test_groq_health_unhealthy():
    provider = GroqProvider(api_key="gsk-mock-key")
    with patch("httpx.AsyncClient.get", new_callable=AsyncMock) as mock_get:
        mock_get.side_effect = httpx.ConnectError("Connection refused")

        health = await provider.health()
        assert health["status"] == "unhealthy"
        assert health["online"] is False


@pytest.mark.asyncio
async def test_groq_generate_success():
    provider = GroqProvider(api_key="gsk-mock-key")
    with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {
            "choices": [{
                "message": {"content": "Groq LPU réponse ultra-rapide."},
                "finish_reason": "stop"
            }],
            "usage": {
                "prompt_tokens": 12,
                "completion_tokens": 28,
                "total_tokens": 40
            }
        }
        mock_post.return_value = mock_resp

        res = await provider.generate(prompt="Vitesse inférence")
        assert isinstance(res, ProviderResponse)
        assert res.content == "Groq LPU réponse ultra-rapide."
        assert res.cost_class == CostClass.FREE_ENDPOINT
        assert res.provider == "groq"
        assert res.usage["total_tokens"] == 40
        assert res.error_class is None


@pytest.mark.asyncio
async def test_groq_generate_rotation_on_429():
    pool = SovereignKeyPool("groq", ["gsk-key-1", "gsk-key-2"])
    provider = GroqProvider(key_pool=pool)

    # Premier appel 429, second appel 200
    mock_resp_429 = MagicMock()
    mock_resp_429.status_code = 429
    mock_resp_429.text = "Rate limit exceeded"

    mock_resp_200 = MagicMock()
    mock_resp_200.status_code = 200
    mock_resp_200.json.return_value = {
        "choices": [{
            "message": {"content": "Succès après rotation."},
            "finish_reason": "stop"
        }],
        "usage": {"prompt_tokens": 10, "completion_tokens": 20, "total_tokens": 30}
    }

    with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
        mock_post.side_effect = [mock_resp_429, mock_resp_200]

        res = await provider.generate(prompt="Test rotation")
        assert res.content == "Succès après rotation."
        assert res.error_class is None
        assert mock_post.call_count == 2


@pytest.mark.asyncio
async def test_groq_stream():
    provider = GroqProvider(api_key="gsk-mock-key")
    chunks = [
        b'data: {"choices": [{"delta": {"content": "Vitesse "}}]}\n',
        b'data: {"choices": [{"delta": {"content": "Groq!"}}]}\n',
        b'data: [DONE]\n',
    ]

    class MockStreamResponse:
        def raise_for_status(self):
            pass

        async def aiter_lines(self):
            for c in chunks:
                yield c.decode("utf-8").strip()

        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc_val, exc_tb):
            pass

    with patch("httpx.AsyncClient.stream", return_value=MockStreamResponse()):
        tokens = []
        async for token in provider.stream(prompt="Stream test"):
            tokens.append(token)
        assert tokens == ["Vitesse ", "Groq!"]
