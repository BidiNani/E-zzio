"""Identité souveraine : jamais Google, toujours E-ZZIO/BidiNani."""
from core.providers.base_provider import SYSTEM_IDENTITY


def test_identity_names_ezzio_and_creator():
    assert "E-ZZIO" in SYSTEM_IDENTITY
    assert "BidiNani" in SYSTEM_IDENTITY


def test_identity_denies_google():
    assert "PAS un assistant Google" in SYSTEM_IDENTITY
    assert "PAS un modèle généraliste nommé Gemini" in SYSTEM_IDENTITY


def test_gemini_sdk_uses_identity_by_default():
    from core.providers.gemini_provider import GeminiProvider
    p = GeminiProvider(api_key="K0")
    payload = p._build_generation_payload("ping")
    text = payload["systemInstruction"]["parts"][0]["text"]
    assert "E-ZZIO" in text and "BidiNani" in text


def test_ollama_defaults_to_identity():
    import asyncio
    from unittest.mock import patch
    from core.providers.ollama_provider import OllamaProvider

    seen = {}

    class FakeResp:
        status_code = 200

        def json(self):
            return {"response": "ok", "done": True}

    class FakeClient:
        async def __aenter__(self):
            return self

        async def __aexit__(self, *a):
            return False

        async def post(self, url, json=None, **kwargs):
            seen["payload"] = json
            return FakeResp()

    async def run():
        import core.providers.ollama_provider as mod
        with patch.object(mod.httpx, "AsyncClient", return_value=FakeClient()):
            return await OllamaProvider().generate(prompt="ping")

    r = asyncio.run(run())
    assert r.error_class is None
    assert "E-ZZIO" in seen["payload"]["system"]
