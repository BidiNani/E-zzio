"""
E-ZZIO Test Suite — Composio Capability Qualification Certification.
Certifie l'intégration sécurisée de Composio sous le Capability Qualification Framework :
- Fail-Closed en l'absence de clé COMPOSIO_API_KEY
- Scopes de lecture autorisés (ALLOW)
- Scopes d'écriture avec obligation d'approbation humaine (REQUIRE_HUMAN)
- Intégration et dispatch via CapabilityRegistry
"""
from unittest.mock import MagicMock, patch

import httpx
import pytest

from core.capabilities.capability_qualification import QualificationStatus
from core.capabilities.composio_provider import ComposioProvider
from core.capabilities.registry import capability_registry


@pytest.mark.asyncio
async def test_composio_provider_unconfigured_fail_closed(tmp_path):
    provider = ComposioProvider(workspace_root=str(tmp_path))
    provider.api_key = None  # Clé absente

    res = await provider.list_available_apps()
    assert res["ok"] is True
    assert res["configured"] is False
    assert res["status"] == "UNCONFIGURED_FAIL_CLOSED"
    assert "github" in res["supported_apps"]

    exec_res = await provider.execute_action("github_create_issue", {"title": "Bug"}, is_write=False)
    assert exec_res["ok"] is False
    assert "Fail-Closed" in exec_res["error"]


@pytest.mark.asyncio
async def test_composio_provider_read_allowed(tmp_path):
    provider = ComposioProvider(workspace_root=str(tmp_path))
    provider.api_key = "mock_composio_key_123"

    mock_resp = httpx.Response(200, json={"items": [{"name": "github"}, {"name": "slack"}]})

    with patch.object(httpx.AsyncClient, "get", return_value=mock_resp):
        res = await provider.list_available_apps()
        assert res["ok"] is True
        assert res["configured"] is True
        assert len(res["apps"]) == 2


@pytest.mark.asyncio
async def test_composio_provider_write_requires_human(tmp_path):
    provider = ComposioProvider(workspace_root=str(tmp_path))
    provider.api_key = "mock_composio_key_123"

    # Action d'écriture (ex: suppression ou modification SaaS)
    res = await provider.execute_action("notion_delete_page", {"page_id": "123"}, is_write=True)
    assert res["ok"] is False
    assert res["requires_human"] is True
    assert res["status"] == "PENDING_APPROVAL"
    assert "requiert approbation humaine" in res["reason"]


@pytest.mark.asyncio
async def test_composio_capability_registry_dispatch():
    # 1. Vérification enregistrement
    qualif = capability_registry.get_qualification("composio-tools")
    assert qualif is not None
    assert qualif.status == QualificationStatus.QUALIFIED
    assert qualif.category == "saas"
    assert "COMPOSIO_API_KEY" in qualif.secrets_required

    # 2. Exécution via le registre en mode unconfigured
    with patch.object(capability_registry.composio_provider, "is_configured", return_value=False):
        res = await capability_registry.execute_capability("composio-tools", {"action": "list_apps"})
        assert res["ok"] is True
        assert res["configured"] is False
