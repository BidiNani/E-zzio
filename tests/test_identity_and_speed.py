"""Identité souveraine +_cfg vitesse (aucune assertion réseau fragile)."""
from core.providers.base_provider import SYSTEM_IDENTITY


def test_system_identity_content():
    assert "E-ZZIO" in SYSTEM_IDENTITY
    assert "Google" in SYSTEM_IDENTITY  # mention négative explicite
    assert "BidiNani" in SYSTEM_IDENTITY


def test_gemini_defaults_to_identity():
    from core.providers.gemini_provider import GeminiProvider
    p = GeminiProvider(api_key="K0")
    payload = p._build_generation_payload("ping")
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
    assert "E-ZZIO" in seen["payload"]["system"]


def test_speed_defaults_bounded():
    from core.agent.coder_federation import CoderModelFederationRouter
    import inspect
    sig = inspect.signature(CoderModelFederationRouter.execute_task)
    assert sig.parameters["temperature"].default <= 0.4
    assert sig.parameters["max_tokens"].default <= 1024


def test_master_injects_identity_without_system():
    import asyncio
    from unittest.mock import AsyncMock, MagicMock
    from core.ezzio_master import EzzioMaster
    from core.providers.base_provider import CostClass, ProviderResponse

    fed = MagicMock()
    fed.execute_task = AsyncMock(return_value=ProviderResponse(
        content="ok", model="m", provider="p", cost_class=CostClass.LOCAL))
    fed._record_audit = MagicMock()
    master = EzzioMaster(federation_router=fed)
    master._memory_initialized = True
    master.memory = MagicMock()

    async def fake_hist(*a, **k):
        return []

    master.memory.get_session_history = fake_hist
    master.memory.record_message = AsyncMock()
    master.memory.init = AsyncMock()
    asyncio.run(master.execute_intent(user_prompt="Bonjour", session_id=""))
    kwargs = fed.execute_task.await_args.kwargs
    assert kwargs["system_prompt"] is not None
    assert "E-zzio" in kwargs["system_prompt"]
