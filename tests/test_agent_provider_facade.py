"""tests/test_agent_provider_facade.py

Tests constitutionnels prouvant que AgentProviderAdapter est une façade
de compatibilité déléguant à la chaîne canonique sans autorité propre.
"""
from unittest.mock import AsyncMock

import pytest

from core.agent.agent_provider import AgentProviderAdapter
from core.cognition.cognitive_gateway import CognitiveGateway
from core.cognition.model_router import ModelRouter
from core.providers.base_provider import ProviderResponse
from core.providers.registry import ProviderFactory
from core.routing.model_registry import canonical_model_registry


def test_e_f_g_adapter_uses_canonical_authority(monkeypatch):
    """TEST E/F/G: AgentProviderAdapter utilise ModelRouter et ProviderFactory, sans autorité propre."""
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
            content="Facade response ok",
            model="gemini-3.7-flash",
            provider="gemini",
        ))
        return fake_prov

    monkeypatch.setattr(ProviderFactory, "create", mock_create)

    adapter = AgentProviderAdapter()
    res = adapter.chat_completion(messages=[{"role": "user", "content": "Test prompt"}])

    assert res == "Facade response ok"
    assert len(router_called) > 0, "TEST E ÉCHOUÉ : ModelRouter n'a pas été consulté par AgentProviderAdapter !"
    assert "gemini" in factory_called, "TEST F ÉCHOUÉ : ProviderFactory.create() n'a pas été appelé !"


def test_j_registry_changes_reflected_in_adapter(monkeypatch):
    """TEST J: Une modification du registre canonique se répercute sur AgentProviderAdapter."""
    factory_called_with_models = []

    def mock_select(self, **kwargs):
        rec = canonical_model_registry.get_by_role("STANDARD_CHAT")
        model_name = rec.name if rec else "gemini-3.5-flash-lite"
        return {"provider": "gemini", "model": model_name, "thinking_level": "off", "role": "STANDARD_CHAT"}

    monkeypatch.setattr(ModelRouter, "select_engine", mock_select)

    def mock_create(name: str, **kwargs):
        fake_prov = AsyncMock()
        async def fake_gen(*args, **gen_kwargs):
            factory_called_with_models.append(gen_kwargs.get("model"))
            return ProviderResponse(content="OK", model=gen_kwargs.get("model", ""), provider="gemini")
        fake_prov.generate = fake_gen
        return fake_prov

    monkeypatch.setattr(ProviderFactory, "create", mock_create)

    adapter = AgentProviderAdapter()
    adapter.chat_completion(messages=[{"role": "user", "content": "Hello"}])

    expected_model = canonical_model_registry.get_by_role("STANDARD_CHAT").name
    assert expected_model in factory_called_with_models, f"TEST J ÉCHOUÉ : Le modèle du registre {expected_model} n'a pas été transmitted !"


@pytest.mark.asyncio
async def test_h_i_cognitive_gateway_compatibility(monkeypatch):
    """TEST H/I: CognitiveGateway utilise la façade AgentProviderAdapter qui atteint la chaîne canonique."""
    factory_calls = []

    def mock_create(name: str, **kwargs):
        factory_calls.append(name)
        fake_prov = AsyncMock()
        fake_prov.generate = AsyncMock(return_value=ProviderResponse(
            content="CognitiveGateway test answer",
            model="gemini-3.7-flash",
            provider="gemini",
        ))
        return fake_prov

    monkeypatch.setattr(ProviderFactory, "create", mock_create)

    gateway = CognitiveGateway(db_path="runtime/evidence/test_evidence.db")
    gateway.memory_gateway = AsyncMock()
    gateway.memory_gateway.init = AsyncMock()
    gateway.memory_gateway.search_memory = AsyncMock(return_value={})
    gateway.memory_gateway.get_session_history = AsyncMock(return_value=[])

    res = await gateway.ask_async("Question test gateway", session_id="test-gw-sess")

    assert res["status"] == "ACCEPTED"
    assert "CognitiveGateway test answer" in res["result"]
    assert "gemini" in factory_calls, "TEST I ÉCHOUÉ : La chaîne n'a pas atteint ProviderFactory !"
