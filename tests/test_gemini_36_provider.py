"""Provider Gemini 3.6-flash : défaut, rotation 429, hiérarchie fédération."""
import collections

import pytest

from core.providers.gemini_provider import GeminiProvider


def test_default_model_is_36_flash():
    p = GeminiProvider(api_key="K0")
    assert p.model == "gemini-3.6-flash"
    assert GeminiProvider.DEFAULT_MODEL == "gemini-3.6-flash"
    assert "gemini-2.5-flash" not in GeminiProvider.FALLBACK_MODELS


def test_no_25_flash_reference():
    import pathlib
    src = pathlib.Path("core/providers/gemini_provider.py").read_text(encoding="utf-8")
    assert "gemini-2.5-flash" not in src


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
    from unittest.mock import patch

    q = collections.deque([_api_error(429), _FakeResp()])
    p = GeminiProvider(api_key="K0")
    with patch("core.config.secrets_loader.gemini_keys", return_value=["K0", "K1"]):
        import google.genai as genai_pkg

        with patch.object(genai_pkg, "Client") as mock_client:
            mock_client.side_effect = lambda api_key=None: _FakeClient(api_key, q)
            r = await p.generate(prompt="ping")
    assert r.error_class is None
    assert r.content == "hi"
    assert mock_client.call_args_list[0].kwargs.get("api_key") == "K0"
    assert mock_client.call_args_list[1].kwargs.get("api_key") == "K1"


def test_federation_hierarchy_intact():
    from core.agent.coder_federation import CoderModelFederationRouter
    assert "gemini" in CoderModelFederationRouter.DEFAULT_MODELS
    assert "ollama" in CoderModelFederationRouter.DEFAULT_MODELS
    assert "nvidia" not in CoderModelFederationRouter.DEFAULT_MODELS


def test_no_chat_session_usage():
    import pathlib
    src = pathlib.Path("core/providers/gemini_provider.py").read_text(encoding="utf-8")
    assert "chats.create" not in src
    assert "send_message_async" not in src


def test_sdk_config_always_carries_identity():
    import asyncio
    from unittest.mock import patch
    import core.providers.gemini_provider as mod

    seen = {}

    class FakeModels:
        async def generate_content(self, model=None, contents=None, config=None):
            seen["system"] = getattr(config, "system_instruction", None)
            seen["model"] = model

            class R:
                text = "ok"
                usage_metadata = None
            return R()

    class FakeAio:
        models = FakeModels()

    class FakeClient:
        def __init__(self, api_key=None):
            pass

        @property
        def aio(self):
            return FakeAio()

    async def run():
        import google.genai as genai_pkg
        with patch.object(genai_pkg, "Client", side_effect=lambda api_key=None: FakeClient()):
            p = mod.GeminiProvider(api_key="K0")
            r = await p.generate(prompt="Qui es-tu ?", model="gemini-3.6-flash")
            assert r.error_class is None

    asyncio.run(run())
    assert "E-ZZIO" in (seen["system"] or "")
    assert seen["model"] == "gemini-3.6-flash"
