"""Tests pour core/coding/providers.py.

Couvre :
- ProviderResponse (dataclass)
- BaseProvider (is_available, pick_model, call NotImplemented)
- GeminiProvider.call (succes, erreurs, pas de cle, pas de modele)
- GroqProvider.call (idem)
- OpenRouterProvider.call (idem, + api_key optionnelle)
- NvidiaProvider.call (idem)
- get_provider (factory)
- get_all_available (ordre priorite)
"""
from __future__ import annotations

import os
from unittest.mock import MagicMock, patch

import pytest

from core.coding.providers import (
    BaseProvider,
    GeminiProvider,
    GroqProvider,
    NvidiaProvider,
    OpenRouterProvider,
    ProviderResponse,
    get_all_available,
    get_provider,
)

# ============================================================
# 1. ProviderResponse
# ============================================================

class TestProviderResponse:
    def test_default_init(self):
        r = ProviderResponse(success=True)
        assert r.success is True
        assert r.content == ""
        assert r.model_used == ""
        assert r.provider == ""
        assert r.error == ""
        assert r.raw is None

    def test_full_init(self):
        r = ProviderResponse(
            success=True,
            content="hello",
            model_used="gemini-3.8",
            provider="gemini",
            raw={"k": "v"},
        )
        assert r.content == "hello"
        assert r.model_used == "gemini-3.8"
        assert r.provider == "gemini"
        assert r.raw == {"k": "v"}

    def test_failure_response(self):
        r = ProviderResponse(success=False, error="boom", provider="groq")
        assert r.success is False
        assert r.error == "boom"
        assert r.provider == "groq"


# ============================================================
# 2. BaseProvider
# ============================================================

class TestBaseProvider:
    def test_init_no_key(self, monkeypatch):
        monkeypatch.delenv("FAKE_KEY", raising=False)
        class FakeProvider(BaseProvider):
            name = "fake"
            api_key_env = "FAKE_KEY"
        p = FakeProvider()
        assert p.api_key == ""

    def test_init_with_key(self, monkeypatch):
        monkeypatch.setenv("FAKE_KEY", "secret123")
        class FakeProvider(BaseProvider):
            name = "fake"
            api_key_env = "FAKE_KEY"
        p = FakeProvider()
        assert p.api_key == "secret123"

    def test_is_available_without_key(self):
        class FakeProvider(BaseProvider):
            name = "fake"
            api_key_env = "FAKE_KEY_ABSENT"
        p = FakeProvider()
        assert p.is_available() is False

    def test_is_available_ollama_always_true(self):
        class OllamaLike(BaseProvider):
            name = "ollama"
            api_key_env = "NEVER_SET"
        p = OllamaLike()
        # ollama retourne toujours True
        assert p.is_available() is True

    def test_pick_model_not_implemented(self):
        p = BaseProvider()
        with pytest.raises(NotImplementedError):
            p.pick_model()

    def test_call_not_implemented(self):
        p = BaseProvider()
        with pytest.raises(NotImplementedError):
            p.call("prompt")


# ============================================================
# 3. GeminiProvider
# ============================================================

class TestGeminiProvider:
    def test_name_and_key_env(self):
        assert GeminiProvider.name == "gemini"
        assert GeminiProvider.api_key_env == "GEMINI_API_KEY"

    def test_call_no_api_key(self, monkeypatch):
        monkeypatch.delenv("GEMINI_API_KEY", raising=False)
        p = GeminiProvider()
        p.api_key = ""
        result = p.call("test prompt")
        assert result.success is False
        assert "GEMINI_API_KEY absent" in result.error
        assert result.provider == "gemini"

    def test_call_no_model_available(self, monkeypatch):
        monkeypatch.setenv("GEMINI_API_KEY", "fake-key")
        p = GeminiProvider()
        with patch.object(p, "pick_model", return_value=None):
            result = p.call("test prompt")
        assert result.success is False
        assert "Aucun modele Gemini disponible" in result.error or "Aucun mod" in result.error

    def test_call_success(self, monkeypatch):
        monkeypatch.setenv("GEMINI_API_KEY", "fake-key")
        p = GeminiProvider()

        mock_response = MagicMock()
        mock_response.raise_for_status = MagicMock()
        mock_response.json = MagicMock(return_value={
            "candidates": [
                {"content": {"parts": [{"text": "Bonjour du LLM"}]}}
            ]
        })
        mock_client = MagicMock()
        mock_client.__enter__ = MagicMock(return_value=mock_client)
        mock_client.__exit__ = MagicMock(return_value=False)
        mock_client.post = MagicMock(return_value=mock_response)

        with patch("core.coding.providers.httpx.Client", return_value=mock_client):
            result = p.call("test prompt", model_id="gemini-3.8-flash")

        assert result.success is True
        assert result.content == "Bonjour du LLM"
        assert result.model_used == "gemini-3.8-flash"
        assert result.provider == "gemini"

    def test_call_success_auto_pick_model(self, monkeypatch):
        monkeypatch.setenv("GEMINI_API_KEY", "fake-key")
        p = GeminiProvider()

        mock_model = MagicMock()
        mock_model.model_id = "gemini-auto-picked"

        mock_response = MagicMock()
        mock_response.raise_for_status = MagicMock()
        mock_response.json = MagicMock(return_value={
            "candidates": [{"content": {"parts": [{"text": "OK"}]}}]
        })
        mock_client = MagicMock()
        mock_client.__enter__ = MagicMock(return_value=mock_client)
        mock_client.__exit__ = MagicMock(return_value=False)
        mock_client.post = MagicMock(return_value=mock_response)

        with patch.object(p, "pick_model", return_value=mock_model):
            with patch("core.coding.providers.httpx.Client", return_value=mock_client):
                result = p.call("test prompt")

        assert result.success is True
        assert result.model_used == "gemini-auto-picked"

    def test_call_http_error(self, monkeypatch):
        monkeypatch.setenv("GEMINI_API_KEY", "fake-key")
        p = GeminiProvider()

        mock_client = MagicMock()
        mock_client.__enter__ = MagicMock(return_value=mock_client)
        mock_client.__exit__ = MagicMock(return_value=False)
        mock_client.post = MagicMock(side_effect=RuntimeError("HTTP 500"))

        with patch("core.coding.providers.httpx.Client", return_value=mock_client):
            result = p.call("test", model_id="x")

        assert result.success is False
        assert "HTTP 500" in result.error
        assert result.provider == "gemini"


# ============================================================
# 4. GroqProvider
# ============================================================

class TestGroqProvider:
    def test_name_and_key_env(self):
        assert GroqProvider.name == "groq"
        assert GroqProvider.api_key_env == "GROQ_API_KEY"

    def test_call_no_api_key(self, monkeypatch):
        monkeypatch.delenv("GROQ_API_KEY", raising=False)
        p = GroqProvider()
        p.api_key = ""
        result = p.call("test")
        assert result.success is False
        assert "GROQ_API_KEY absent" in result.error

    def test_call_no_model_available(self, monkeypatch):
        monkeypatch.setenv("GROQ_API_KEY", "fake-key")
        p = GroqProvider()
        with patch.object(p, "pick_model", return_value=None):
            result = p.call("test")
        assert result.success is False

    def test_call_success(self, monkeypatch):
        monkeypatch.setenv("GROQ_API_KEY", "fake-key")
        p = GroqProvider()

        mock_response = MagicMock()
        mock_response.raise_for_status = MagicMock()
        mock_response.json = MagicMock(return_value={
            "choices": [{"message": {"content": "Reponse Groq"}}]
        })
        mock_client = MagicMock()
        mock_client.__enter__ = MagicMock(return_value=mock_client)
        mock_client.__exit__ = MagicMock(return_value=False)
        mock_client.post = MagicMock(return_value=mock_response)

        with patch("core.coding.providers.httpx.Client", return_value=mock_client):
            result = p.call("test", model_id="qwen3.8-27b")

        assert result.success is True
        assert result.content == "Reponse Groq"
        assert result.model_used == "qwen3.8-27b"

    def test_call_http_error(self, monkeypatch):
        monkeypatch.setenv("GROQ_API_KEY", "fake-key")
        p = GroqProvider()

        mock_client = MagicMock()
        mock_client.__enter__ = MagicMock(return_value=mock_client)
        mock_client.__exit__ = MagicMock(return_value=False)
        mock_client.post = MagicMock(side_effect=RuntimeError("429 Too Many Requests"))

        with patch("core.coding.providers.httpx.Client", return_value=mock_client):
            result = p.call("test", model_id="x")

        assert result.success is False
        assert "429" in result.error


# ============================================================
# 5. OpenRouterProvider
# ============================================================

class TestOpenRouterProvider:
    def test_name_and_key_env(self):
        assert OpenRouterProvider.name == "openrouter"
        assert OpenRouterProvider.api_key_env == "OPENROUTER_API_KEY"

    def test_call_no_model_available(self, monkeypatch):
        monkeypatch.setenv("OPENROUTER_API_KEY", "fake-key")
        p = OpenRouterProvider()
        with patch.object(p, "pick_model", return_value=None):
            result = p.call("test")
        assert result.success is False

    def test_call_success_with_key(self, monkeypatch):
        monkeypatch.setenv("OPENROUTER_API_KEY", "fake-key")
        p = OpenRouterProvider()

        mock_response = MagicMock()
        mock_response.raise_for_status = MagicMock()
        mock_response.json = MagicMock(return_value={
            "choices": [{"message": {"content": "Reponse OpenRouter"}}]
        })
        mock_client = MagicMock()
        mock_client.__enter__ = MagicMock(return_value=mock_client)
        mock_client.__exit__ = MagicMock(return_value=False)
        mock_client.post = MagicMock(return_value=mock_response)

        with patch("core.coding.providers.httpx.Client", return_value=mock_client):
            result = p.call("test", model_id="glm-5.2")

        assert result.success is True
        assert result.content == "Reponse OpenRouter"

    def test_call_success_without_key_optional(self, monkeypatch):
        # OpenRouter fonctionne sans cle (free tier)
        monkeypatch.delenv("OPENROUTER_API_KEY", raising=False)
        p = OpenRouterProvider()
        p.api_key = ""

        mock_response = MagicMock()
        mock_response.raise_for_status = MagicMock()
        mock_response.json = MagicMock(return_value={
            "choices": [{"message": {"content": "OK"}}]
        })
        mock_client = MagicMock()
        mock_client.__enter__ = MagicMock(return_value=mock_client)
        mock_client.__exit__ = MagicMock(return_value=False)
        mock_client.post = MagicMock(return_value=mock_response)

        with patch("core.coding.providers.httpx.Client", return_value=mock_client):
            result = p.call("test", model_id="free-model")

        assert result.success is True

    def test_call_http_error(self, monkeypatch):
        monkeypatch.setenv("OPENROUTER_API_KEY", "fake-key")
        p = OpenRouterProvider()

        mock_client = MagicMock()
        mock_client.__enter__ = MagicMock(return_value=mock_client)
        mock_client.__exit__ = MagicMock(return_value=False)
        mock_client.post = MagicMock(side_effect=RuntimeError("503 down"))

        with patch("core.coding.providers.httpx.Client", return_value=mock_client):
            result = p.call("test", model_id="x")

        assert result.success is False
        assert "503" in result.error


# ============================================================
# 6. NvidiaProvider
# ============================================================

class TestNvidiaProvider:
    def test_name_and_key_env(self):
        assert NvidiaProvider.name == "nvidia"
        assert NvidiaProvider.api_key_env == "NVIDIA_API_KEY"

    def test_call_no_api_key(self, monkeypatch):
        monkeypatch.delenv("NVIDIA_API_KEY", raising=False)
        p = NvidiaProvider()
        p.api_key = ""
        result = p.call("test")
        assert result.success is False
        assert "NVIDIA_API_KEY absent" in result.error

    def test_call_no_model_available(self, monkeypatch):
        monkeypatch.setenv("NVIDIA_API_KEY", "fake-key")
        p = NvidiaProvider()
        with patch.object(p, "pick_model", return_value=None):
            result = p.call("test")
        assert result.success is False

    def test_call_success(self, monkeypatch):
        monkeypatch.setenv("NVIDIA_API_KEY", "fake-key")
        p = NvidiaProvider()

        mock_response = MagicMock()
        mock_response.raise_for_status = MagicMock()
        mock_response.json = MagicMock(return_value={
            "choices": [{"message": {"content": "Reponse Nvidia"}}]
        })
        mock_client = MagicMock()
        mock_client.__enter__ = MagicMock(return_value=mock_client)
        mock_client.__exit__ = MagicMock(return_value=False)
        mock_client.post = MagicMock(return_value=mock_response)

        with patch("core.coding.providers.httpx.Client", return_value=mock_client):
            result = p.call("test", model_id="nemotron")

        assert result.success is True
        assert result.content == "Reponse Nvidia"

    def test_call_http_error(self, monkeypatch):
        monkeypatch.setenv("NVIDIA_API_KEY", "fake-key")
        p = NvidiaProvider()

        mock_client = MagicMock()
        mock_client.__enter__ = MagicMock(return_value=mock_client)
        mock_client.__exit__ = MagicMock(return_value=False)
        mock_client.post = MagicMock(side_effect=RuntimeError("500 error"))

        with patch("core.coding.providers.httpx.Client", return_value=mock_client):
            result = p.call("test", model_id="x")

        assert result.success is False


# ============================================================
# 7. get_provider (factory)
# ============================================================

class TestGetProvider:
    def test_gemini(self):
        p = get_provider("gemini")
        assert isinstance(p, GeminiProvider)

    def test_groq(self):
        p = get_provider("groq")
        assert isinstance(p, GroqProvider)

    def test_openrouter(self):
        p = get_provider("openrouter")
        assert isinstance(p, OpenRouterProvider)

    def test_nvidia(self):
        p = get_provider("nvidia")
        assert isinstance(p, NvidiaProvider)

    def test_case_insensitive(self):
        p = get_provider("GEMINI")
        assert isinstance(p, GeminiProvider)

    def test_unknown_returns_none(self):
        assert get_provider("unknown_xyz") is None


# ============================================================
# 8. get_all_available
# ============================================================

class TestGetAllAvailable:
    def test_empty_when_no_keys(self, monkeypatch):
        for env in ("GROQ_API_KEY", "GEMINI_API_KEY", "OPENROUTER_API_KEY", "NVIDIA_API_KEY"):
            monkeypatch.delenv(env, raising=False)
        result = get_all_available()
        # Aucun provider avec cle -> liste vide
        assert result == []

    def test_only_groq_with_key(self, monkeypatch):
        for env in ("GEMINI_API_KEY", "OPENROUTER_API_KEY", "NVIDIA_API_KEY"):
            monkeypatch.delenv(env, raising=False)
        monkeypatch.setenv("GROQ_API_KEY", "fake-groq")
        result = get_all_available()
        names = [p.name for p in result]
        assert "groq" in names
        assert "gemini" not in names

    def test_order_priority(self, monkeypatch):
        # Toutes les cles presentes
        for env in ("GROQ_API_KEY", "GEMINI_API_KEY", "OPENROUTER_API_KEY", "NVIDIA_API_KEY"):
            monkeypatch.setenv(env, "fake")
        result = get_all_available()
        names = [p.name for p in result]
        # Ordre attendu : groq, gemini, openrouter, nvidia
        assert names == ["groq", "gemini", "openrouter", "nvidia"]

    def test_subset_order_preserved(self, monkeypatch):
        for env in ("GEMINI_API_KEY", "OPENROUTER_API_KEY", "NVIDIA_API_KEY"):
            monkeypatch.delenv(env, raising=False)
        monkeypatch.setenv("GROQ_API_KEY", "fake")
        result = get_all_available()
        assert len(result) >= 1
        assert result[0].name == "groq"
