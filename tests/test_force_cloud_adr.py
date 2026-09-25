"""tests/test_force_cloud_adr.py

Contract tests for force_cloud canonical behavior (ADR-force_cloud.md).

Coverage:
  T1 — ADR R1 : route already cloud → no substitution
  T2 — ADR R2 : route local + cloud record exists → uses registry values
  T3 — ADR R3 : REASONING (no cloud equivalent) → RouteIntegrityError
  T4 — ADR R2/R4 : provider and model come from registry, not hardcoded
"""
from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from core.agent.agent_provider import AgentProviderAdapter, RouteIntegrityError
from core.cognition.model_router import ModelRouter
from core.providers.base_provider import ProviderResponse
from core.providers.registry import ProviderFactory


# ─────────────────────────────────────────────────────────────────────────────
# T1 — ADR R1 : route nominale déjà cloud → force_cloud ne modifie rien
# ─────────────────────────────────────────────────────────────────────────────
@pytest.mark.asyncio
async def test_force_cloud_noop_when_route_already_cloud(monkeypatch):
    """ADR R1 : Si provider nominal != ollama, force_cloud=True est silencieux."""

    def mock_select(self, **kwargs):
        return {
            "provider": "gemini",
            "model": "gemini-3.8-flash",
            "thinking_level": "off",
            "role": "MASTER",
        }

    monkeypatch.setattr(ModelRouter, "select_engine", mock_select)

    factory_calls: list[str] = []
    model_calls: list[str] = []

    def mock_create(name: str, **kwargs):
        factory_calls.append(name)
        fake = AsyncMock()

        async def fake_gen(*args, **gen_kwargs):
            model_calls.append(gen_kwargs.get("model", ""))
            return ProviderResponse(
                content="cloud ok", model=gen_kwargs.get("model", ""), provider=name
            )

        fake.generate = fake_gen
        return fake

    monkeypatch.setattr(ProviderFactory, "create", mock_create)

    adapter = AgentProviderAdapter()
    res = await adapter.chat_completion_async(
        messages=[{"role": "user", "content": "test"}],
        force_cloud=True,
    )

    assert res == "cloud ok"
    # Provider inchangé : gemini (pas de substitution)
    assert factory_calls == ["gemini"], f"Provider inattendu : {factory_calls}"
    # Modèle inchangé : gemini-3.8-flash (pas de substitution)
    assert model_calls == ["gemini-3.8-flash"], f"Model inattendu : {model_calls}"


# ─────────────────────────────────────────────────────────────────────────────
# T2 — ADR R2 : route locale + cloud record disponible → provider/model du registry
# ─────────────────────────────────────────────────────────────────────────────
@pytest.mark.asyncio
async def test_force_cloud_uses_registry_when_cloud_record_exists(monkeypatch):
    """ADR R2 : provider et modèle proviennent du registry, pas d'un hardcode."""

    def mock_select(self, **kwargs):
        return {
            "provider": "ollama",
            "model": "qwen2.5-coder:7b-instruct-q4_K_M",
            "thinking_level": "off",
            "role": "LOCAL_CODING",
        }

    monkeypatch.setattr(ModelRouter, "select_engine", mock_select)

    # Hypothétique : le registry dispose d'un équivalent cloud pour LOCAL_CODING
    mock_cloud_rec = MagicMock()
    mock_cloud_rec.provider = "gemini"
    mock_cloud_rec.name = "gemini-3.7-flash"

    factory_calls: list[str] = []
    model_calls: list[str] = []

    def mock_create(name: str, **kwargs):
        factory_calls.append(name)
        fake = AsyncMock()

        async def fake_gen(*args, **gen_kwargs):
            model_calls.append(gen_kwargs.get("model", ""))
            return ProviderResponse(
                content="registry cloud ok",
                model=gen_kwargs.get("model", ""),
                provider=name,
            )

        fake.generate = fake_gen
        return fake

    monkeypatch.setattr(ProviderFactory, "create", mock_create)

    with patch(
        "core.agent.agent_provider.canonical_model_registry"
    ) as mock_registry:
        mock_registry.resolve_cloud_role.return_value = mock_cloud_rec

        adapter = AgentProviderAdapter()
        res = await adapter.chat_completion_async(
            messages=[{"role": "user", "content": "test"}],
            force_cloud=True,
        )

    assert res == "registry cloud ok"
    # Le provider vient du registry
    assert factory_calls == [mock_cloud_rec.provider], (
        f"Provider attendu '{mock_cloud_rec.provider}', obtenu {factory_calls}"
    )
    # Le modèle vient du registry
    assert model_calls == [mock_cloud_rec.name], (
        f"Model attendu '{mock_cloud_rec.name}', obtenu {model_calls}"
    )
    # Le registry a été consulté avec le rôle original
    mock_registry.resolve_cloud_role.assert_called_once_with("LOCAL_CODING")



# ─────────────────────────────────────────────────────────────────────────────
# T3 — ADR R3 : REASONING (ollama-only dans ROLE_MAP) → RouteIntegrityError
# ─────────────────────────────────────────────────────────────────────────────
@pytest.mark.asyncio
async def test_force_cloud_fail_closed_for_reasoning_role(monkeypatch):
    """ADR R3 : REASONING + force_cloud=True → RouteIntegrityError car aucun cloud n'existe."""

    def mock_select(self, **kwargs):
        return {
            "provider": "ollama",
            "model": "deepseek-r1:7b",
            "thinking_level": "low",
            "role": "REASONING",
        }

    monkeypatch.setattr(ModelRouter, "select_engine", mock_select)

    factory_calls: list[str] = []

    def mock_create(name: str, **kwargs):
        factory_calls.append(name)
        return AsyncMock()

    monkeypatch.setattr(ProviderFactory, "create", mock_create)

    adapter = AgentProviderAdapter()
    with pytest.raises(RouteIntegrityError) as exc_info:
        await adapter.chat_completion_async(
            messages=[{"role": "user", "content": "test"}],
            force_cloud=True,
        )

    err = str(exc_info.value)
    # Message fail-closed obligatoire
    assert "[FAIL-CLOSED]" in err, f"'[FAIL-CLOSED]' absent du message : {err!r}"
    # Rôle lisible dans le message
    assert "REASONING" in err, f"'REASONING' absent du message : {err!r}"
    # Aucun provider instancié : pas d'exécution réelle
    assert factory_calls == [], (
        f"ProviderFactory.create() ne doit pas être appelé avant le fail-closed, "
        f"appelé avec : {factory_calls}"
    )


# ─────────────────────────────────────────────────────────────────────────────
# T4 — ADR R4 : gemini-3.7-flash n'est pas hardcodé dans la branche force_cloud
# ─────────────────────────────────────────────────────────────────────────────
@pytest.mark.asyncio
async def test_force_cloud_does_not_hardcode_gemini_37_flash(monkeypatch):
    """ADR R4 : Lorsqu'un cloud record existe, le provider/model vient du registry,
    pas d'une constante 'gemini-3.7-flash' écrite en dur."""

    def mock_select(self, **kwargs):
        return {
            "provider": "ollama",
            "model": "hermes3:8b",
            "thinking_level": "off",
            "role": "LOCAL_AGENT",
        }

    monkeypatch.setattr(ModelRouter, "select_engine", mock_select)

    # Cloud record avec un provider/modèle différent de gemini-3.7-flash
    mock_cloud_rec = MagicMock()
    mock_cloud_rec.provider = "groq"
    mock_cloud_rec.name = "llama-3.3-70b-versatile"

    factory_calls: list[str] = []
    model_calls: list[str] = []

    def mock_create(name: str, **kwargs):
        factory_calls.append(name)
        fake = AsyncMock()

        async def fake_gen(*args, **gen_kwargs):
            model_calls.append(gen_kwargs.get("model", ""))
            return ProviderResponse(
                content="groq response",
                model=gen_kwargs.get("model", ""),
                provider=name,
            )

        fake.generate = fake_gen
        return fake

    monkeypatch.setattr(ProviderFactory, "create", mock_create)

    with patch(
        "core.agent.agent_provider.canonical_model_registry"
    ) as mock_registry:
        mock_registry.resolve_cloud_role.return_value = mock_cloud_rec

        adapter = AgentProviderAdapter()
        res = await adapter.chat_completion_async(
            messages=[{"role": "user", "content": "test"}],
            force_cloud=True,
        )


    assert res == "groq response"
    # Provider = groq (pas gemini)
    assert factory_calls == ["groq"], (
        f"gemini-3.7-flash hardcodé détecté — provider attendu 'groq', obtenu {factory_calls}"
    )
    # Modèle = ce que le registry retourne (pas gemini-3.7-flash)
    assert model_calls == ["llama-3.3-70b-versatile"], (
        f"gemini-3.7-flash hardcodé détecté — model attendu 'llama-3.3-70b-versatile', obtenu {model_calls}"
    )
    # Pas de 'gemini-3.7-flash' dans les appels
    assert "gemini-3.7-flash" not in model_calls, (
        "gemini-3.7-flash est encore hardcodé dans la branche force_cloud"
    )
