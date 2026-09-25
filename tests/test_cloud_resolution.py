"""
tests/test_cloud_resolution.py — Verification of force_cloud resolution policy.
"""
import sys
from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest

ROOT_DIR = Path(r"G:\AI\E-zzio")
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from core.agent.agent_provider import AgentProviderAdapter, RouteIntegrityError
from core.providers.base_provider import ProviderResponse
from core.routing.model_registry import (
    CanonicalModelRecord,
    CanonicalModelRegistry,
    ModelSource,
    canonical_model_registry,
)

# ----------------------------------------------------------------------
# 1. Registry Level Tests
# ----------------------------------------------------------------------

def test_cloud_resolution_already_cloud():
    """Test Registry : Rôle cloud existant (CODING -> gemini-3.7-flash) + force_cloud -> cible canonique valide."""
    registry = CanonicalModelRegistry()
    target = registry.resolve_cloud_role("CODING")
    assert target is not None, "Expected valid cloud target for CODING"
    assert target.name == "gemini-3.7-flash"
    assert target.provider != "ollama"


def test_cloud_resolution_local_only_fail_closed():
    """Test Registry : Rôle local sans équivalent cloud (REASONING -> deepseek-r1:7b) + force_cloud -> FAIL-CLOSED."""
    registry = CanonicalModelRegistry()
    target = registry.resolve_cloud_role("REASONING")
    assert target is None, "Expected FAIL-CLOSED (None) for REASONING under force_cloud"


def test_cloud_resolution_ambiguity_fail_closed():
    """Test Registry : Ambiguïté architecturale (>1 candidats cloud) -> FAIL-CLOSED."""
    registry = CanonicalModelRegistry()
    record_extra = CanonicalModelRecord(
        name="gemini-3.9-coding",
        source=ModelSource.GEMINI,
        provider="gemini",
        role="CODING",
        roles=["CODING"],
    )
    registry._models.append(record_extra)

    target = registry.resolve_cloud_role("CODING")
    assert target is None, "Expected FAIL-CLOSED (None) when >1 cloud candidates exist"


# ----------------------------------------------------------------------
# 2. AgentProviderAdapter Level Tests
# ----------------------------------------------------------------------

@pytest.mark.asyncio
async def test_adapter_already_cloud():
    """A. Déjà cloud : provider et model restent inchangés."""
    adapter = AgentProviderAdapter()
    messages = [{"role": "user", "content": "Hello"}]

    mock_resp = ProviderResponse(content="OK Cloud", provider="gemini", model="gemini-3.7-flash")

    with patch("core.agent.agent_provider.ProviderFactory.create") as mock_factory:
        mock_prov = AsyncMock()
        mock_prov.generate.return_value = mock_resp
        mock_factory.return_value = mock_prov

        res = await adapter.chat_completion_async(messages, force_cloud=True, speed="coding")
        assert res == "OK Cloud"
        mock_factory.assert_called_once_with("gemini")
        mock_prov.generate.assert_called_once()
        assert mock_prov.generate.call_args.kwargs["model"] == "gemini-3.7-flash"


@pytest.mark.asyncio
async def test_adapter_local_with_canonical_cloud_target():
    """B. Local + cible cloud canonique : bascule vers la cible cloud canonique."""
    adapter = AgentProviderAdapter()
    messages = [{"role": "user", "content": "Code something"}]

    mock_routing = {
        "provider": "ollama",
        "model": "qwen2.5-coder:7b-instruct-q4_K_M",
        "role": "CODING",
        "thinking_level": "off",
    }
    mock_resp = ProviderResponse(content="Code Result", provider="gemini", model="gemini-3.7-flash")

    with patch.object(adapter.router, "select_engine", return_value=mock_routing), \
         patch("core.agent.agent_provider.ProviderFactory.create") as mock_factory:
        mock_prov = AsyncMock()
        mock_prov.generate.return_value = mock_resp
        mock_factory.return_value = mock_prov

        res = await adapter.chat_completion_async(messages, force_cloud=True, speed="coding")
        assert res == "Code Result"
        mock_factory.assert_called_once_with("gemini")
        assert mock_prov.generate.call_args.kwargs["model"] == "gemini-3.7-flash"


@pytest.mark.asyncio
async def test_adapter_local_no_cloud_target_fail_closed():
    """C. Local + aucune cible cloud (REASONING) -> RouteIntegrityError fail-closed, aucun Provider.generate()."""
    adapter = AgentProviderAdapter()
    messages = [{"role": "user", "content": "Think deep"}]

    mock_routing = {
        "provider": "ollama",
        "model": "deepseek-r1:7b",
        "role": "REASONING",
        "thinking_level": "low",
    }

    with patch.object(adapter.router, "select_engine", return_value=mock_routing), \
         patch("core.agent.agent_provider.ProviderFactory.create") as mock_factory:
        with pytest.raises(RouteIntegrityError) as exc_info:
            await adapter.chat_completion_async(messages, force_cloud=True)

        assert "FAIL-CLOSED" in str(exc_info.value)
        assert "REASONING" in str(exc_info.value)
        mock_factory.assert_not_called()


@pytest.mark.asyncio
async def test_adapter_multiple_cloud_targets_fail_closed():
    """D. Plusieurs cibles cloud pour un rôle -> RouteIntegrityError fail-closed, pas de sélection arbitraire."""
    adapter = AgentProviderAdapter()
    messages = [{"role": "user", "content": "Code something"}]

    mock_routing = {
        "provider": "ollama",
        "model": "qwen2.5-coder:7b-instruct-q4_K_M",
        "role": "CODING",
        "thinking_level": "off",
    }

    # Temporairement ajouter un second record cloud 'CODING' pour induire une ambiguïté (>1)
    record_extra = CanonicalModelRecord(
        name="gemini-3.9-coding",
        source=ModelSource.GEMINI,
        provider="gemini",
        role="CODING",
        roles=["CODING"],
    )
    canonical_model_registry._models.append(record_extra)

    try:
        with patch.object(adapter.router, "select_engine", return_value=mock_routing), \
             patch("core.agent.agent_provider.ProviderFactory.create") as mock_factory:
            with pytest.raises(RouteIntegrityError) as exc_info:
                await adapter.chat_completion_async(messages, force_cloud=True)

            assert "FAIL-CLOSED" in str(exc_info.value)
            mock_factory.assert_not_called()
    finally:
        # Nettoyage
        if record_extra in canonical_model_registry._models:
            canonical_model_registry._models.remove(record_extra)
