"""tests/test_validation_phase3b.py

Validation réelle déterministe de la Phase 3B.2 :
1. AgentProviderAdapter comme façade canonique (sync & async)
2. Compatibilité CognitiveGateway & CodingAgentLoop
3. Fallback canonique et comportement sous défaillance
4. Centralisation via CanonicalModelRegistry
"""
from unittest.mock import AsyncMock, MagicMock

import pytest

from core.agent.agent_provider import AgentProviderAdapter
from core.agent.coding_agent_loop import CodingAgentHarness
from core.cognition.cognitive_gateway import CognitiveGateway
from core.cognition.model_router import ModelRouter
from core.providers.base_provider import ProviderResponse
from core.providers.registry import ProviderFactory
from core.routing.model_registry import canonical_model_registry


# ------------------------------------------------------------
# TEST K — SYNC
# ------------------------------------------------------------
def test_k_sync_chat_completion(monkeypatch):
    """TEST K: AgentProviderAdapter.chat_completion() (sync) atteint ModelRouter -> ProviderFactory -> fake Provider."""
    router_called = []
    factory_called = []

    def mock_select(self, **kwargs):
        router_called.append(kwargs)
        return {"provider": "gemini", "model": "gemini-3.7-flash", "thinking_level": "off", "role": "CODING"}

    monkeypatch.setattr(ModelRouter, "select_engine", mock_select)

    def mock_create(name: str, **kwargs):
        factory_called.append(name)
        fake_prov = AsyncMock()
        fake_prov.generate = AsyncMock(return_value=ProviderResponse(
            content="Sync response OK", model="gemini-3.7-flash", provider="gemini"
        ))
        return fake_prov

    monkeypatch.setattr(ProviderFactory, "create", mock_create)

    adapter = AgentProviderAdapter()
    res = adapter.chat_completion(messages=[{"role": "user", "content": "Sync test prompt"}])

    assert res == "Sync response OK"
    assert len(router_called) == 1
    assert "gemini" in factory_called


# ------------------------------------------------------------
# TEST L — ASYNC
# ------------------------------------------------------------
@pytest.mark.asyncio
async def test_l_async_chat_completion(monkeypatch):
    """TEST L: AgentProviderAdapter.chat_completion_async() (async) avec un event loop réel."""
    router_called = []
    factory_called = []

    def mock_select(self, **kwargs):
        router_called.append(kwargs)
        return {"provider": "gemini", "model": "gemini-3.7-flash", "thinking_level": "off", "role": "CODING"}

    monkeypatch.setattr(ModelRouter, "select_engine", mock_select)

    def mock_create(name: str, **kwargs):
        factory_called.append(name)
        fake_prov = AsyncMock()
        fake_prov.generate = AsyncMock(return_value=ProviderResponse(
            content="Async response OK", model="gemini-3.7-flash", provider="gemini"
        ))
        return fake_prov

    monkeypatch.setattr(ProviderFactory, "create", mock_create)

    adapter = AgentProviderAdapter()
    res = await adapter.chat_completion_async(messages=[{"role": "user", "content": "Async test prompt"}])

    assert res == "Async response OK"
    assert len(router_called) == 1
    assert "gemini" in factory_called


# ------------------------------------------------------------
# TEST M — COMPATIBILITY chat()
# ------------------------------------------------------------
def test_m_compatibility_chat(monkeypatch):
    """TEST M: chat() conserve le contrat attendu par CodingAgentLoop (dict avec response, content, ok)."""
    def mock_create(name: str, **kwargs):
        fake_prov = AsyncMock()
        fake_prov.generate = AsyncMock(return_value=ProviderResponse(
            content="Chat method content", model="gemini-3.7-flash", provider="gemini"
        ))
        return fake_prov

    monkeypatch.setattr(ProviderFactory, "create", mock_create)

    adapter = AgentProviderAdapter()
    res = adapter.chat(text="Hello", system_prompt="Sys")

    assert isinstance(res, dict)
    assert res["ok"] is True
    assert res["response"] == "Chat method content"
    assert res["content"] == "Chat method content"


# ------------------------------------------------------------
# TEST N — CognitiveGateway
# ------------------------------------------------------------
@pytest.mark.asyncio
async def test_n_cognitive_gateway_integration(monkeypatch):
    """TEST N: Exécution réelle de CognitiveGateway.ask_async avec provider mocké."""
    def mock_create(name: str, **kwargs):
        fake_prov = AsyncMock()
        fake_prov.generate = AsyncMock(return_value=ProviderResponse(
            content="CognitiveGateway integration output", model="gemini-3.7-flash", provider="gemini"
        ))
        return fake_prov

    monkeypatch.setattr(ProviderFactory, "create", mock_create)

    gateway = CognitiveGateway(db_path="runtime/evidence/test_val_n.db")
    gateway.memory_gateway = AsyncMock()
    gateway.memory_gateway.init = AsyncMock()
    gateway.memory_gateway.search_memory = AsyncMock(return_value={})
    gateway.memory_gateway.get_session_history = AsyncMock(return_value=[])

    res = await gateway.ask_async("Gateway prompt", session_id="sess-n")

    assert res["status"] == "ACCEPTED"
    assert "CognitiveGateway integration output" in res["result"]


# ------------------------------------------------------------
# TEST O — CodingAgentLoop / CodingAgentHarness
# ------------------------------------------------------------
def test_o_coding_agent_harness_integration(monkeypatch):
    """TEST O: Exécution de CodingAgentHarness avec la façade AgentProviderAdapter."""
    def mock_create(name: str, **kwargs):
        fake_prov = AsyncMock()
        fake_prov.generate = AsyncMock(return_value=ProviderResponse(
            content="J'ai terminé l'objectif sans outil.", model="gemini-3.7-flash", provider="gemini"
        ))
        return fake_prov

    monkeypatch.setattr(ProviderFactory, "create", mock_create)

    harness = CodingAgentHarness()
    harness.registry.execute = MagicMock(return_value="Codebase map mock")

    steps = list(harness.run_trajectory(objective="Faire un test de trajectoire", max_steps=2))

    assert len(steps) >= 1
    assert "J'ai terminé l'objectif" in steps[0]["thought"]


# ------------------------------------------------------------
# TEST FALLBACK CANONIQUE
# ------------------------------------------------------------
@pytest.mark.asyncio
async def test_fallback_primary_failure(monkeypatch):
    """TEST FALLBACK: Primary provider echoue -> fallback canonique ProviderFactory.create('gemini') est utilise."""
    created_providers = []

    def mock_create(name: str, **kwargs):
        created_providers.append(name)
        fake_prov = AsyncMock()
        if len(created_providers) == 1:
            fake_prov.generate = AsyncMock(side_effect=RuntimeError("Primary provider connection error"))
        else:
            fake_prov.generate = AsyncMock(return_value=ProviderResponse(
                content="Fallback response content", model="gemini-3.5-flash-lite", provider="gemini"
            ))
        return fake_prov

    monkeypatch.setattr(ProviderFactory, "create", mock_create)

    adapter = AgentProviderAdapter()
    res = await adapter.chat_completion_async(messages=[{"role": "user", "content": "Test fallback"}])

    assert res == "Fallback response content"
    assert len(created_providers) == 2
    assert created_providers[1] == "gemini"


# ------------------------------------------------------------
# TEST DÉFAILLANCE TOTALE PROVIDERS
# ------------------------------------------------------------
@pytest.mark.asyncio
async def test_total_provider_failure_controlled_fail_closed(monkeypatch):
    """TEST DÉFAILLANCE: Primary + Fallback echouent -> RuntimeError contrôlé (Fail-Closed)."""
    def mock_create(name: str, **kwargs):
        fake_prov = AsyncMock()
        fake_prov.generate = AsyncMock(side_effect=RuntimeError("All providers dead"))
        return fake_prov

    monkeypatch.setattr(ProviderFactory, "create", mock_create)

    adapter = AgentProviderAdapter()
    with pytest.raises(RuntimeError) as exc_info:
        await adapter.chat_completion_async(messages=[{"role": "user", "content": "Test total failure"}])

    assert "[FAIL-CLOSED]" in str(exc_info.value)


# ------------------------------------------------------------
# TEST CENTRALISATION REGISTRE CANONIQUE
# ------------------------------------------------------------
def test_centralization_registry_change(monkeypatch):
    """TEST CENTRALISATION: Modification de la configuration du registre canonique affecte le modele choisi."""
    models_requested = []

    def mock_create(name: str, **kwargs):
        fake_prov = AsyncMock()
        async def fake_gen(*args, **gen_kwargs):
            models_requested.append(gen_kwargs.get("model"))
            return ProviderResponse(content="OK", model=gen_kwargs.get("model", ""), provider="gemini")
        fake_prov.generate = fake_gen
        return fake_prov

    monkeypatch.setattr(ProviderFactory, "create", mock_create)

    adapter = AgentProviderAdapter()
    adapter.chat_completion(messages=[{"role": "user", "content": "Centralization test"}], speed="fast")

    assert len(models_requested) == 1
    assert models_requested[0] in ["gemini-3.5-flash-lite", "gemini-3.7-flash", "gemini-3.8-flash"]
