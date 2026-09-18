"""Anti-bypass : Discord passe par les endpoints gouvernés, identité injectée.

Contexte : le chemin canonique est /master/chat → EzzioMaster → GeminiProvider.
Plus de fédération : gouvernance simplifiée, audit direct, fail-closed.
"""
import time
from pathlib import Path

SRC = Path("core/integrations/discord/discord_client.py").read_text(encoding="utf-8")


def test_no_direct_provider_in_discord_client():
    for mod in ("GeminiProvider", "GroqProvider", "OllamaProvider",
                "coder_federation", "genai", "litellm"):
        assert mod not in SRC, f"bypass direct interdit : {mod}"


def test_discord_goes_through_governed_endpoints():
    assert "/master/chat" in SRC
    assert "/v1/chat/completions" in SRC


def test_identity_present_on_fast_path():
    import asyncio
    from unittest.mock import AsyncMock, MagicMock

    from core.ezzio_master import EzzioMaster
    from core.providers.base_provider import CostClass, ProviderResponse

    # Mock direct du provider Gemini (plus de fédération)
    provider = MagicMock()
    provider.generate = AsyncMock(return_value=ProviderResponse(
        content="ok", model="gemini-3.6-flash", provider="gemini",
        cost_class=CostClass.FREE_ENDPOINT))
    master = EzzioMaster(provider=provider)
    master._memory_initialized = True
    master.memory = MagicMock()
    master.memory.get_session_history = AsyncMock(return_value=[])
    master.memory.record_message = AsyncMock()
    master.memory.init = AsyncMock()

    async def run():
        return await master.execute_intent(user_prompt="Qui es-tu ?",
                                           speed="fast", session_id="")

    res = asyncio.run(run())
    # Vérifie que l'appel provider a reçu le system_prompt avec l'identité
    kwargs = provider.generate.await_args.kwargs
    assert kwargs["system_prompt"] is not None
    assert "E-ZZIO" in kwargs["system_prompt"]
    assert res["ok"] is True
    assert res["authority"] == "CanonicalIdentity"
    assert res["model"] == "gemini-3.6-flash"
    assert res["provider"] == "gemini"


def test_execute_intent_fail_closed_on_empty():
    import asyncio
    from unittest.mock import AsyncMock, MagicMock

    from core.ezzio_master import EzzioMaster
    from core.providers.base_provider import CostClass, ProviderResponse

    provider = MagicMock()
    provider.generate = AsyncMock(return_value=ProviderResponse(
        content="", model="gemini-3.6-flash", provider="gemini",
        cost_class=CostClass.FREE_ENDPOINT))
    master = EzzioMaster(provider=provider)
    master._memory_initialized = True
    master.memory = MagicMock()
    master.memory.get_session_history = AsyncMock(return_value=[])
    master.memory.record_message = AsyncMock()
    master.memory.init = AsyncMock()

    async def run():
        return await master.execute_intent(user_prompt="test", session_id="")

    res = asyncio.run(run())
    assert res["ok"] is False
    assert "[FAIL-CLOSED]" in res["response"]
    assert res["model"] == "none"
    assert res["provider"] == "none"
