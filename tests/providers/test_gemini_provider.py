import pytest
import json
import httpx
from unittest.mock import patch, AsyncMock, MagicMock
from core.providers.base_provider import (
    BaseProvider,
    CostClass,
    ProviderAvailability,
    ProviderErrorClass,
    ProviderResponse,
)
from core.providers.iresearch_provider import IResearchProvider
from core.providers.gemini_provider import GeminiProvider


def test_gemini_provider_structure():
    provider = GeminiProvider(api_key="mock-key")
    assert provider.name == "gemini"
    assert "generativelanguage" in provider.base_url
    assert isinstance(provider, BaseProvider)
    assert isinstance(provider, IResearchProvider)


def test_gemini_availability():
    provider = GeminiProvider(api_key="mock-key")
    assert provider.availability() == ProviderAvailability.AVAILABLE
    assert provider.is_available() is True


def test_gemini_cost_class():
    provider = GeminiProvider(api_key="mock-key")
    assert provider.cost_class() == CostClass.FREE_ENDPOINT


def test_gemini_capabilities():
    provider = GeminiProvider(api_key="mock-key")
    caps = provider.capabilities()
    assert "TEXT" in caps
    assert "VISION" in caps
    assert "FAST_INFERENCE" in caps
    caps_37 = provider.capabilities("gemini-3.7-flash")
    assert "REASONING" in caps_37


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
def test_gemini_error_mapping(status_code, expected_class):
    provider = GeminiProvider(api_key="mock-key")
    assert provider.error_mapping(status_code) == expected_class


@pytest.mark.parametrize("thinking_level,expected_budget", [
    ("off", 0),
    ("low", 1024),
    ("medium", 8192),
    ("high", 24576),
])
def test_gemini_thinking_policy(thinking_level, expected_budget):
    provider = GeminiProvider(api_key="mock_key")
    payload = provider._build_generation_payload("Calcul complexe", thinking_level=thinking_level)
    assert payload["generationConfig"]["thinkingConfig"]["thinkingBudget"] == expected_budget


@pytest.mark.asyncio
async def test_gemini_health_healthy():
    provider = GeminiProvider(api_key="mock-key")
    with patch("httpx.AsyncClient.get", new_callable=AsyncMock) as mock_get:
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {"models": [{"name": "models/gemini-3.5-flash"}]}
        mock_get.return_value = mock_resp

        health = await provider.health()
        assert health["status"] == "healthy"
        assert health["online"] is True
        assert provider.availability() == ProviderAvailability.AVAILABLE


@pytest.mark.asyncio
async def test_gemini_health_unhealthy():
    provider = GeminiProvider(api_key="mock-key")
    with patch("httpx.AsyncClient.get", new_callable=AsyncMock) as mock_get:
        mock_get.side_effect = httpx.ConnectError("Connection refused")

        health = await provider.health()
        assert health["status"] == "unhealthy"
        assert health["online"] is False
        assert provider.availability() == ProviderAvailability.UNAVAILABLE


@pytest.mark.asyncio
async def test_gemini_generate_success():
    provider = GeminiProvider(api_key="mock-key")
    fake_json = {
        "candidates": [{"content": {"parts": [{"text": "Gemini Cloud répond."}]}}]
    }
    with patch("httpx.AsyncClient.post") as mock_post:
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = fake_json
        mock_post.return_value = mock_resp

        res = await provider.generate(prompt="Bonjour")
        assert isinstance(res, ProviderResponse)
        assert res.content == "Gemini Cloud répond."
        assert res.cost_class == CostClass.FREE_ENDPOINT
        assert res.provider == "gemini"
        assert res.error_class is None


@pytest.mark.asyncio
async def test_gemini_generate_unauthorized():
    provider = GeminiProvider(api_key="invalid-key")
    with patch("httpx.AsyncClient.post") as mock_post:
        mock_resp = MagicMock()
        mock_resp.status_code = 401
        mock_resp.text = "Unauthorized"
        mock_post.return_value = mock_resp

        res = await provider.generate(prompt="Test")
        assert res.error_class == ProviderErrorClass.UNAUTHORIZED
        assert res.content == ""
        assert provider.availability() == ProviderAvailability.UNAUTHORIZED


@pytest.mark.asyncio
async def test_gemini_stream():
    provider = GeminiProvider(api_key="mock-key")
    chunks = [
        b'data: {"candidates": [{"content": {"parts": [{"text": "Bonjour "}]}}]}\n',
        b'data: {"candidates": [{"content": {"parts": [{"text": "monde!"}]}}]}\n',
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
        async for token in provider.stream(prompt="Salut"):
            tokens.append(token)
        assert tokens == ["Bonjour ", "monde!"]


@pytest.mark.asyncio
async def test_gemini_search_backwards_compatible():
    provider = GeminiProvider(api_key="mock-key")
    fake_json = {
        "candidates": [{"content": {"parts": [{"text": "Synthèse Gemini."}]}}]
    }
    with patch("httpx.AsyncClient.post") as mock_post:
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = fake_json
        mock_post.return_value = mock_resp

        res = await provider.search("recherche")
        assert res["provider"] == "gemini"
        assert res["data"]["text"] == "Synthèse Gemini."
