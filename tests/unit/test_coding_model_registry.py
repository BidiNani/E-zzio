"""Tests pour core/coding/model_registry.py."""
from __future__ import annotations

from unittest.mock import MagicMock, patch

from core.coding.model_registry import (
    CACHE_TTL,
    GEMINI_EXCLUDED_PATTERNS,
    GROQ_EXCLUDED_PATTERNS,
    MIN_GEMINI_VERSION,
    MODEL_PRIORITIES,
    ModelInfo,
    ModelRegistry,
    _gemini_version_rank,
    _is_valid_gemini,
    _is_valid_groq,
    get_registry,
)


def _mock_httpx(response_data):
    """Cree un mock httpx.Client qui retourne response_data."""
    mock_response = MagicMock()
    mock_response.raise_for_status = MagicMock()
    mock_response.json = MagicMock(return_value=response_data)
    mock_client = MagicMock()
    mock_client.__enter__ = MagicMock(return_value=mock_client)
    mock_client.__exit__ = MagicMock(return_value=False)
    mock_client.get = MagicMock(return_value=mock_response)
    return mock_client


# ============================================================
# 1. Constantes
# ============================================================

class TestConstants:
    def test_cache_ttl(self):
        assert CACHE_TTL == 3600

    def test_min_gemini_version(self):
        assert MIN_GEMINI_VERSION == 3.5

    def test_gemini_excluded_patterns(self):
        assert "tts" in GEMINI_EXCLUDED_PATTERNS
        assert "embed" in GEMINI_EXCLUDED_PATTERNS
        assert "gemma" in GEMINI_EXCLUDED_PATTERNS
        assert "preview" in GEMINI_EXCLUDED_PATTERNS

    def test_groq_excluded_patterns(self):
        assert "whisper" in GROQ_EXCLUDED_PATTERNS
        assert "guard" in GROQ_EXCLUDED_PATTERNS
        assert "embed" in GROQ_EXCLUDED_PATTERNS

    def test_model_priorities_has_gemini(self):
        assert "gemini-3.8-flash" in MODEL_PRIORITIES
        assert MODEL_PRIORITIES["gemini-3.8-flash"] == 100

    def test_model_priorities_has_groq(self):
        assert "qwen/qwen3.8-27b" in MODEL_PRIORITIES

    def test_model_priorities_has_openrouter(self):
        assert "z-ai/glm-5.2:free" in MODEL_PRIORITIES


# ============================================================
# 2. ModelInfo
# ============================================================

class TestModelInfo:
    def test_default_init(self):
        m = ModelInfo(provider="gemini", model_id="gemini-3.8-flash")
        assert m.provider == "gemini"
        assert m.model_id == "gemini-3.8-flash"
        assert m.display_name == ""
        assert m.context_length == 0
        assert m.is_free is True
        assert m.version_rank == 0.0
        assert m.raw == {}

    def test_full_init(self):
        m = ModelInfo(
            provider="groq",
            model_id="qwen-27b",
            display_name="Qwen 27B",
            context_length=8192,
            is_free=False,
            version_rank=3.8,
            raw={"k": "v"},
        )
        assert m.display_name == "Qwen 27B"
        assert m.context_length == 8192
        assert m.is_free is False
        assert m.version_rank == 3.8
        assert m.raw == {"k": "v"}

    def test_raw_default_factory(self):
        m1 = ModelInfo(provider="x", model_id="a")
        m2 = ModelInfo(provider="x", model_id="b")
        m1.raw["key"] = "value"
        assert "key" not in m2.raw


# ============================================================
# 3. _gemini_version_rank
# ============================================================

class TestGeminiVersionRank:
    def test_standard_version(self):
        assert _gemini_version_rank("gemini-3.8-flash") == 3.8

    def test_3_5(self):
        assert _gemini_version_rank("gemini-3.5-flash-lite") == 3.5

    def test_2_5(self):
        assert _gemini_version_rank("gemini-2.5-pro") == 2.5

    def test_no_version_returns_zero(self):
        assert _gemini_version_rank("gemini-flash") == 0.0

    def test_case_insensitive(self):
        assert _gemini_version_rank("GEMINI-3.8-FLASH") == 3.8

    def test_integer_version(self):
        result = _gemini_version_rank("gemini-3-flash")
        assert result == 3.0

    def test_complex_version(self):
        result = _gemini_version_rank("gemini-4.5-preview-05-2026")
        assert result == 4.5


# ============================================================
# 4. _is_valid_gemini
# ============================================================

class TestIsValidGemini:
    def test_valid_3_8(self):
        assert _is_valid_gemini("gemini-3.8-flash") is True

    def test_valid_3_5_lite(self):
        assert _is_valid_gemini("gemini-3.5-flash-lite") is True

    def test_invalid_2_5_too_old(self):
        assert _is_valid_gemini("gemini-2.5-pro") is False

    def test_invalid_preview(self):
        assert _is_valid_gemini("gemini-3.8-flash-preview") is False

    def test_invalid_gemma(self):
        assert _is_valid_gemini("gemma-4-31b-it") is False

    def test_invalid_tts(self):
        assert _is_valid_gemini("gemini-tts-3.5") is False

    def test_invalid_embed(self):
        assert _is_valid_gemini("gemini-3.8-embed") is False

    def test_invalid_no_version(self):
        assert _is_valid_gemini("gemini-flash") is False


# ============================================================
# 5. _is_valid_groq
# ============================================================

class TestIsValidGroq:
    def test_valid_qwen(self):
        assert _is_valid_groq("qwen/qwen3.8-27b") is True

    def test_valid_gpt_oss(self):
        assert _is_valid_groq("openai/gpt-oss-120b") is True

    def test_invalid_whisper(self):
        assert _is_valid_groq("whisper-large-v3") is False

    def test_invalid_guard(self):
        assert _is_valid_groq("llama-guard-3-8b") is False

    def test_invalid_embed(self):
        assert _is_valid_groq("nomic-embed-text") is False

    def test_invalid_tts(self):
        assert _is_valid_groq("playai-tts") is False

    def test_invalid_orpheus(self):
        assert _is_valid_groq("canopylabs/orpheus-v1") is False

    def test_invalid_allam(self):
        assert _is_valid_groq("allam-2-7b") is False


# ============================================================
# 6. ModelRegistry init + _load_keys
# ============================================================

class TestModelRegistryInit:
    def test_default_cache_ttl(self):
        r = ModelRegistry()
        assert r.cache_ttl == CACHE_TTL

    def test_custom_cache_ttl(self):
        r = ModelRegistry(cache_ttl=60)
        assert r.cache_ttl == 60

    def test_cache_empty_initially(self):
        r = ModelRegistry()
        assert r._cache == {}

    def test_load_keys_no_env(self, monkeypatch):
        for var in ("GEMINI_API_KEY", "GROQ_API_KEY", "OPENROUTER_API_KEY", "NVIDIA_API_KEY"):
            monkeypatch.delenv(var, raising=False)
        r = ModelRegistry()
        assert r._keys == {}

    def test_load_keys_one_env(self, monkeypatch):
        for var in ("GEMINI_API_KEY", "OPENROUTER_API_KEY", "NVIDIA_API_KEY"):
            monkeypatch.delenv(var, raising=False)
        monkeypatch.setenv("GROQ_API_KEY", "fake-groq")
        r = ModelRegistry()
        assert r._keys == {"groq": "fake-groq"}

    def test_load_keys_all_env(self, monkeypatch):
        monkeypatch.setenv("GEMINI_API_KEY", "g")
        monkeypatch.setenv("GROQ_API_KEY", "gr")
        monkeypatch.setenv("OPENROUTER_API_KEY", "or")
        monkeypatch.setenv("NVIDIA_API_KEY", "nv")
        r = ModelRegistry()
        assert r._keys == {
            "gemini": "g",
            "groq": "gr",
            "openrouter": "or",
            "nvidia": "nv",
        }


# ============================================================
# 7. _is_cache_valid
# ============================================================

class TestIsCacheValid:
    def test_no_cache(self):
        r = ModelRegistry()
        assert r._is_cache_valid("gemini") is False

    def test_valid_cache(self):
        import time
        r = ModelRegistry(cache_ttl=3600)
        r._cache["gemini"] = (time.time(), [])
        assert r._is_cache_valid("gemini") is True

    def test_expired_cache(self):
        import time
        r = ModelRegistry(cache_ttl=1)
        r._cache["gemini"] = (time.time() - 10, [])
        assert r._is_cache_valid("gemini") is False


# ============================================================
# 8. list_models
# ============================================================

class TestListModels:
    def test_unknown_provider_returns_empty(self):
        r = ModelRegistry()
        result = r.list_models("unknown_xyz")
        assert result == []

    def test_uses_cache_when_valid(self):
        import time
        r = ModelRegistry()
        cached = [ModelInfo(provider="gemini", model_id="x")]
        r._cache["gemini"] = (time.time(), cached)
        result = r.list_models("gemini")
        assert result is cached

    def test_force_refresh_ignores_cache(self):
        # FIX : mock _fetch_gemini pour ne pas dependre des cles d'environnement
        import time
        r = ModelRegistry()
        r._cache["gemini"] = (time.time(), [ModelInfo(provider="old", model_id="x")])
        with patch.object(r, "_fetch_gemini", return_value=[]):
            result = r.list_models("gemini", force_refresh=True)
            assert result == []

    def test_fetch_exception_caught(self):
        r = ModelRegistry()
        with patch.object(r, "_fetch_gemini", side_effect=RuntimeError("boom")):
            result = r.list_models("gemini")
            assert result == []


# ============================================================
# 9. _fetch_gemini
# ============================================================

class TestFetchGemini:
    def test_no_key_returns_empty(self, monkeypatch):
        monkeypatch.delenv("GEMINI_API_KEY", raising=False)
        r = ModelRegistry()
        assert r._fetch_gemini() == []

    def test_success_filters_and_sorts(self, monkeypatch):
        monkeypatch.setenv("GEMINI_API_KEY", "fake")
        r = ModelRegistry()
        api_data = {
            "models": [
                {"name": "models/gemini-3.8-flash", "supportedGenerationMethods": ["generateContent"], "inputTokenLimit": 8192},
                {"name": "models/gemini-3.5-flash", "supportedGenerationMethods": ["generateContent"], "inputTokenLimit": 4096},
                {"name": "models/gemini-2.5-pro", "supportedGenerationMethods": ["generateContent"]},
                {"name": "models/gemma-4-31b", "supportedGenerationMethods": ["generateContent"]},
                {"name": "models/gemini-3.8-embed", "supportedGenerationMethods": ["generateContent"]},
                {"name": "models/gemini-3.7-flash", "supportedGenerationMethods": ["embedContent"]},
            ]
        }
        with patch("core.coding.model_registry.httpx.Client", return_value=_mock_httpx(api_data)):
            result = r._fetch_gemini()

        assert len(result) == 2
        assert result[0].model_id == "gemini-3.8-flash"
        assert result[0].version_rank == 3.8
        assert result[1].model_id == "gemini-3.5-flash"

    def test_empty_models_list(self, monkeypatch):
        monkeypatch.setenv("GEMINI_API_KEY", "fake")
        r = ModelRegistry()
        with patch("core.coding.model_registry.httpx.Client", return_value=_mock_httpx({"models": []})):
            result = r._fetch_gemini()
            assert result == []

    def test_missing_models_key(self, monkeypatch):
        monkeypatch.setenv("GEMINI_API_KEY", "fake")
        r = ModelRegistry()
        with patch("core.coding.model_registry.httpx.Client", return_value=_mock_httpx({})):
            result = r._fetch_gemini()
            assert result == []


# ============================================================
# 10. _fetch_groq
# ============================================================

class TestFetchGroq:
    def test_no_key_returns_empty(self, monkeypatch):
        monkeypatch.delenv("GROQ_API_KEY", raising=False)
        r = ModelRegistry()
        assert r._fetch_groq() == []

    def test_success_filters(self, monkeypatch):
        monkeypatch.setenv("GROQ_API_KEY", "fake")
        r = ModelRegistry()
        api_data = {
            "data": [
                {"id": "qwen/qwen3.8-27b", "context_window": 32768},
                {"id": "whisper-large-v3"},
                {"id": "llama-guard-3-8b"},
                {"id": "openai/gpt-oss-120b", "context_window": 128000},
            ]
        }
        with patch("core.coding.model_registry.httpx.Client", return_value=_mock_httpx(api_data)):
            result = r._fetch_groq()
        assert len(result) == 2
        ids = [m.model_id for m in result]
        assert "qwen/qwen3.8-27b" in ids
        assert "openai/gpt-oss-120b" in ids
        assert "whisper-large-v3" not in ids

    def test_missing_data_key(self, monkeypatch):
        monkeypatch.setenv("GROQ_API_KEY", "fake")
        r = ModelRegistry()
        with patch("core.coding.model_registry.httpx.Client", return_value=_mock_httpx({})):
            result = r._fetch_groq()
            assert result == []


# ============================================================
# 11. _fetch_openrouter
# ============================================================

class TestFetchOpenRouter:
    def test_no_key_still_calls_api(self, monkeypatch):
        monkeypatch.delenv("OPENROUTER_API_KEY", raising=False)
        r = ModelRegistry()
        api_data = {
            "data": [
                {"id": "free-model-1", "pricing": {"prompt": "0", "completion": "0"}, "context_length": 8192},
            ]
        }
        with patch("core.coding.model_registry.httpx.Client", return_value=_mock_httpx(api_data)):
            result = r._fetch_openrouter()
            assert len(result) == 1
            assert result[0].model_id == "free-model-1"

    def test_filters_paid_models(self, monkeypatch):
        monkeypatch.delenv("OPENROUTER_API_KEY", raising=False)
        r = ModelRegistry()
        api_data = {
            "data": [
                {"id": "free-1", "pricing": {"prompt": "0", "completion": "0"}},
                {"id": "paid-1", "pricing": {"prompt": "0.001", "completion": "0.002"}},
                {"id": "free-2", "pricing": {"prompt": "0", "completion": "0"}},
            ]
        }
        with patch("core.coding.model_registry.httpx.Client", return_value=_mock_httpx(api_data)):
            result = r._fetch_openrouter()
            ids = [m.model_id for m in result]
            assert "free-1" in ids
            assert "free-2" in ids
            assert "paid-1" not in ids

    def test_missing_pricing_key(self, monkeypatch):
        monkeypatch.delenv("OPENROUTER_API_KEY", raising=False)
        r = ModelRegistry()
        api_data = {"data": [{"id": "x", "pricing": {}}]}
        with patch("core.coding.model_registry.httpx.Client", return_value=_mock_httpx(api_data)):
            result = r._fetch_openrouter()
            assert result == []


# ============================================================
# 12. _fetch_nvidia
# ============================================================

class TestFetchNvidia:
    def test_no_key_returns_empty(self, monkeypatch):
        monkeypatch.delenv("NVIDIA_API_KEY", raising=False)
        r = ModelRegistry()
        assert r._fetch_nvidia() == []

    def test_success(self, monkeypatch):
        monkeypatch.setenv("NVIDIA_API_KEY", "fake")
        r = ModelRegistry()
        api_data = {"data": [{"id": "nemotron-3-ultra"}, {"id": "llama-3.1-70b"}]}
        with patch("core.coding.model_registry.httpx.Client", return_value=_mock_httpx(api_data)):
            result = r._fetch_nvidia()
            assert len(result) == 2
            assert result[0].model_id == "nemotron-3-ultra"

    def test_http_exception_returns_empty(self, monkeypatch):
        monkeypatch.setenv("NVIDIA_API_KEY", "fake")
        r = ModelRegistry()
        mock_client = MagicMock()
        mock_client.__enter__ = MagicMock(return_value=mock_client)
        mock_client.__exit__ = MagicMock(return_value=False)
        mock_client.get = MagicMock(side_effect=RuntimeError("timeout"))
        with patch("core.coding.model_registry.httpx.Client", return_value=mock_client):
            result = r._fetch_nvidia()
            assert result == []


# ============================================================
# 13. _fetch_ollama
# ============================================================

class TestFetchOllama:
    def test_success(self, monkeypatch):
        monkeypatch.delenv("OLLAMA_HOST", raising=False)
        r = ModelRegistry()
        api_data = {"models": [{"name": "llama3:8b"}, {"name": "mistral:7b"}]}
        with patch("core.coding.model_registry.httpx.Client", return_value=_mock_httpx(api_data)):
            result = r._fetch_ollama()
            assert len(result) == 2
            assert result[0].model_id == "llama3:8b"

    def test_http_exception_returns_empty(self, monkeypatch):
        monkeypatch.delenv("OLLAMA_HOST", raising=False)
        r = ModelRegistry()
        mock_client = MagicMock()
        mock_client.__enter__ = MagicMock(return_value=mock_client)
        mock_client.__exit__ = MagicMock(return_value=False)
        mock_client.get = MagicMock(side_effect=RuntimeError("connection refused"))
        with patch("core.coding.model_registry.httpx.Client", return_value=mock_client):
            result = r._fetch_ollama()
            assert result == []

    def test_missing_models_key(self, monkeypatch):
        monkeypatch.delenv("OLLAMA_HOST", raising=False)
        r = ModelRegistry()
        with patch("core.coding.model_registry.httpx.Client", return_value=_mock_httpx({})):
            result = r._fetch_ollama()
            assert result == []


# ============================================================
# 14. pick_best_for
# ============================================================

class TestPickBestFor:
    def test_returns_none_if_no_models(self, monkeypatch):
        for var in ("GEMINI_API_KEY", "GROQ_API_KEY", "OPENROUTER_API_KEY", "NVIDIA_API_KEY"):
            monkeypatch.delenv(var, raising=False)
        r = ModelRegistry()
        with patch.object(r, "list_models", return_value=[]):
            assert r.pick_best_for("code") is None

    def test_returns_best_by_priority(self, monkeypatch):
        r = ModelRegistry()
        m_low = ModelInfo(provider="gemini", model_id="gemini-3.5-flash")
        m_high = ModelInfo(provider="gemini", model_id="gemini-3.8-flash")
        with patch.object(r, "list_models", return_value=[m_low, m_high]):
            result = r.pick_best_for("code", provider="gemini")
            assert result is m_high

    def test_ignores_models_not_in_priorities(self, monkeypatch):
        r = ModelRegistry()
        m_unknown = ModelInfo(provider="gemini", model_id="unknown-model")
        m_known = ModelInfo(provider="gemini", model_id="gemini-3.5-flash")
        with patch.object(r, "list_models", return_value=[m_unknown, m_known]):
            result = r.pick_best_for("code", provider="gemini")
            assert result is m_known

    def test_searches_all_providers_if_none_specified(self):
        r = ModelRegistry()
        m = ModelInfo(provider="groq", model_id="qwen/qwen3.8-27b")

        def fake_list(provider):
            if provider == "groq":
                return [m]
            return []

        with patch.object(r, "list_models", side_effect=fake_list):
            result = r.pick_best_for("code")
            assert result is m


# ============================================================
# 15. all_free_models
# ============================================================

class TestAllFreeModels:
    def test_empty_when_no_models(self):
        r = ModelRegistry()
        with patch.object(r, "list_models", return_value=[]):
            assert r.all_free_models() == []

    def test_returns_only_free(self):
        r = ModelRegistry()
        free_model = ModelInfo(provider="gemini", model_id="x", is_free=True)
        paid_model = ModelInfo(provider="gemini", model_id="y", is_free=False)

        def fake_list(provider):
            if provider == "gemini":
                return [free_model, paid_model]
            return []

        with patch.object(r, "list_models", side_effect=fake_list):
            result = r.all_free_models()
            assert len(result) == 1
            assert result[0] is free_model


# ============================================================
# 16. get_registry (singleton)
# ============================================================

class TestGetRegistry:
    def test_returns_model_registry(self):
        import core.coding.model_registry as mr
        mr._registry = None
        r = get_registry()
        assert isinstance(r, ModelRegistry)

    def test_singleton_returns_same_instance(self):
        import core.coding.model_registry as mr
        mr._registry = None
        r1 = get_registry()
        r2 = get_registry()
        assert r1 is r2


# ============================================================
# 17. list_models dispatch vers _fetch_* (complement 100%)
# ============================================================

class TestListModelsDispatch:
    """Couvre le dispatch de list_models vers chaque _fetch_*."""

    def test_list_models_groq_dispatches(self):
        r = ModelRegistry()
        mock_model = ModelInfo(provider="groq", model_id="qwen/qwen3.8-27b")
        with patch.object(r, "_fetch_groq", return_value=[mock_model]):
            result = r.list_models("groq")
            assert result == [mock_model]

    def test_list_models_openrouter_dispatches(self):
        r = ModelRegistry()
        mock_model = ModelInfo(provider="openrouter", model_id="z-ai/glm-5.2:free")
        with patch.object(r, "_fetch_openrouter", return_value=[mock_model]):
            result = r.list_models("openrouter")
            assert result == [mock_model]

    def test_list_models_nvidia_dispatches(self):
        r = ModelRegistry()
        mock_model = ModelInfo(provider="nvidia", model_id="nemotron-3-ultra")
        with patch.object(r, "_fetch_nvidia", return_value=[mock_model]):
            result = r.list_models("nvidia")
            assert result == [mock_model]

    def test_list_models_ollama_dispatches(self):
        r = ModelRegistry()
        mock_model = ModelInfo(provider="ollama", model_id="llama3:8b")
        with patch.object(r, "_fetch_ollama", return_value=[mock_model]):
            result = r.list_models("ollama")
            assert result == [mock_model]
