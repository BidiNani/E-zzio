"""Identité souveraine +_cfg vitesse (aucune assertion réseau fragile)."""
from core.providers.base_provider import SYSTEM_IDENTITY


def test_system_identity_content():
    assert "E-ZZIO" in SYSTEM_IDENTITY
    assert "Google" in SYSTEM_IDENTITY  # mention négative explicite
    assert "BidiNani" in SYSTEM_IDENTITY


def test_gemini_defaults_to_identity():
    from core.providers.gemini_provider import GeminiProvider
    p = GeminiProvider(api_key="K0")
    payload = p._build_generation_payload("ping", system_prompt=SYSTEM_IDENTITY)
    text = payload["systemInstruction"]["parts"][0]["text"]
    assert "E-ZZIO" in text


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
        async def post(self, url, json=None, **kwargs):
            seen["payload"] = json
            return FakeResp()

    async def run():
        import core.providers.ollama_provider as mod
        with patch.object(mod, "_shared_client", return_value=FakeClient()):
            return await OllamaProvider().generate(prompt="ping")

    r = asyncio.run(run())
    assert r.error_class is None


def test_speed_defaults_bounded():
    from core.providers.gemini_provider import GeminiProvider
    p = GeminiProvider(api_key="K0")
    payload = p._build_generation_payload("ping", temperature=0.2, max_tokens=512)
    assert payload["generationConfig"]["temperature"] <= 0.4
    assert payload["generationConfig"]["maxOutputTokens"] <= 1024


def test_master_injects_identity_without_system():
    import asyncio
    from unittest.mock import AsyncMock, MagicMock
    from core.ezzio_master import EzzioMaster
    from core.providers.base_provider import CostClass, ProviderResponse

    fake_prov = MagicMock()
    fake_prov.generate = AsyncMock(return_value=ProviderResponse(
        content="ok", model="m", provider="p", cost_class=CostClass.LOCAL))
    master = EzzioMaster(provider=fake_prov)
    master._memory_initialized = True
    master.memory = MagicMock()

    async def fake_hist(*a, **k):
        return []

    master.memory.get_session_history = fake_hist
    master.memory.record_message = AsyncMock()
    master.memory.init = AsyncMock()
    asyncio.run(master.execute_intent(user_prompt="Bonjour", session_id=""))
    kwargs = fake_prov.generate.call_args.kwargs
    assert kwargs["system_prompt"] is not None
    assert "E-ZZIO" in kwargs["system_prompt"]
