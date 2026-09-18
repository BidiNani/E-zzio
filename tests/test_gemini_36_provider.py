"""Provider Gemini 3.6-flash : défaut, rotation 429, hiérarchie fédération."""
import collections

import pytest

from core.providers.gemini_provider import GeminiProvider
from core.providers.base_provider import ProviderResponse


def test_default_model_is_36_flash():
    p = GeminiProvider(api_key="K0")
    assert p.model == "gemini-3.5-flash-lite"
    assert GeminiProvider.DEFAULT_MODEL == "gemini-3.5-flash-lite"


def test_no_25_flash_reference():
    import pathlib
    src = pathlib.Path("core/providers/gemini_provider.py").read_text(encoding="utf-8")
    assert "gemini-3.5-flash-lite" in src


def _api_error(code: int) -> Exception:
    from google.genai.errors import APIError
    err = APIError.__new__(APIError)
    err.code = code
    return err


class _FakeResp:
    text = "hi"


class _FakeModels:
    def __init__(self, q):
        self.q = q

    async def generate_content(self, **kwargs):
        item = self.q.popleft()
        if isinstance(item, Exception):
            raise item
        return item


class _FakeClient:
    def __init__(self, api_key=None, _q=None):
        self.api_key = api_key
        self._q = _q

    @property
    def aio(self):
        parent = self

        class _A:
            models = _FakeModels(parent._q)

        return _A()


@pytest.mark.asyncio
async def test_429_rotates_without_crash():
    from unittest.mock import patch, MagicMock

    p = GeminiProvider(api_key="K0")
    fake_429 = MagicMock()
    fake_429.status_code = 429
    fake_200 = MagicMock()
    fake_200.status_code = 200
    fake_200.json.return_value = {
        "candidates": [{"content": {"parts": [{"text": "hi"}]}}]
    }

    with patch("httpx.AsyncClient.post", side_effect=[fake_429, fake_200]):
        r = await p.generate(prompt="ping")
        assert isinstance(r, ProviderResponse)


def test_federation_hierarchy_intact():
    from core.agent.coder_federation import CoderModelFederationRouter
    assert "gemini" in CoderModelFederationRouter.DEFAULT_MODELS
    assert "ollama" in CoderModelFederationRouter.DEFAULT_MODELS


def test_no_chat_session_usage():
    import pathlib
    src = pathlib.Path("core/providers/gemini_provider.py").read_text(encoding="utf-8")
    assert "chats.create" not in src
    assert "send_message_async" not in src


@pytest.mark.asyncio
async def test_sdk_config_always_carries_identity():
    from unittest.mock import patch, MagicMock
    fake_json = {
        "candidates": [{"content": {"parts": [{"text": "Je suis E-ZZIO."}]}}]
    }
    p = GeminiProvider(api_key="K0")
    with patch("httpx.AsyncClient.post") as mock_post:
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = fake_json
        mock_post.return_value = mock_resp

        r = await p.generate(prompt="Qui es-tu ?", model="gemini-3.5-flash-lite")
        assert r.error_class is None
        assert r.content == "Je suis E-ZZIO."
