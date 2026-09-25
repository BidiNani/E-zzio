"""tests/test_adapter_fallback_alignment.py

Test de régression : vérifie que AgentProviderAdapter utilise le modèle
et le provider de fallback canoniques définis dans FALLBACK_MAP (gemini-3.5-flash).
"""
from unittest.mock import AsyncMock

import pytest

from core.agent.agent_provider import AgentProviderAdapter
from core.cognition.model_router import ModelRouter
from core.providers.base_provider import ProviderResponse
from core.providers.registry import ProviderFactory


@pytest.mark.asyncio
async def test_adapter_fallback_aligns_with_canonical_fallback_map(monkeypatch):
    """Vérifie que le fallback de l'adapter utilise FALLBACK_MAP (gemini-3.5-flash) et non gemini-3.5-flash-lite."""
    created_providers = []
    generated_models = []

    def mock_select(self, **kwargs):
        return {"provider": "gemini", "model": "gemini-3.7-flash", "thinking_level": "off", "role": "CODING"}

    monkeypatch.setattr(ModelRouter, "select_engine", mock_select)

    def mock_create(name: str, **kwargs):
        created_providers.append(name)
        fake_prov = AsyncMock()
        if len(created_providers) == 1:
            fake_prov.generate = AsyncMock(side_effect=RuntimeError("Primary provider error"))
        else:
            async def fake_gen(*args, **gen_kwargs):
                generated_models.append(gen_kwargs.get("model"))
                return ProviderResponse(
                    content="Canonical fallback response",
                    model=gen_kwargs.get("model", ""),
                    provider=name
                )
            fake_prov.generate = fake_gen
        return fake_prov

    monkeypatch.setattr(ProviderFactory, "create", mock_create)

    adapter = AgentProviderAdapter()
    res = await adapter.chat_completion_async(messages=[{"role": "user", "content": "Test prompt"}])

    assert res == "Canonical fallback response"
    assert len(created_providers) == 2
    assert created_providers[1] == "gemini", f"Provider fallback attendu: 'gemini', reçu: '{created_providers[1]}'"
    assert len(generated_models) == 1
    assert generated_models[0] == "gemini-3.5-flash", (
        f"Modèle fallback attendu: 'gemini-3.5-flash', reçu: '{generated_models[0]}'"
    )
