"""
Suite de tests de gouvernance et de pré-vol de sécurité : CapabilityPolicy ↔ CapabilityRegistry.
Valide l'interception stricte des scopes ALLOW, REQUIRE_HUMAN et DENY.
"""
from unittest.mock import AsyncMock, patch

import pytest

from core.capabilities.capability_policy import PolicyDecision
from core.capabilities.registry import CapabilityRegistry, capability_registry


@pytest.mark.asyncio
async def test_allow_scope_dispatches_normally():
    """Vérifie que les scopes ALLOW passent le pré-vol et atteignent le provider."""
    reg = CapabilityRegistry()
    with patch.object(reg.web_provider, "search", new=AsyncMock(return_value={"ok": True, "results": ["hit"]})) as mock_search:
        res = await reg.execute_capability("web-search-mcp", {"query": "python"})
        assert res.get("ok") is True
        assert res.get("results") == ["hit"]
        mock_search.assert_awaited_once_with(query="python", limit=5)


@pytest.mark.asyncio
async def test_allow_scope_github_read():
    """Vérifie que github.read (opération de lecture) est autorisé."""
    reg = CapabilityRegistry()
    with patch.object(reg.github_provider, "get_repo_info", new=AsyncMock(return_value={"ok": True, "repo": "test"})) as mock_gh:
        res = await reg.execute_capability("github-mcp", {"operation": "get_repo_info", "owner": "org", "repo": "test"})
        assert res.get("ok") is True
        mock_gh.assert_awaited_once()


@pytest.mark.asyncio
async def test_require_human_drive_write_intercepted():
    """Vérifie que drive.write est intercepté et bloqué en REQUIRE_HUMAN sans appeler le provider."""
    reg = CapabilityRegistry()
    res = await reg.execute_capability("google-workspace-mcp", {
        "service": "drive",
        "operation": "upload",
        "filename": "critical.doc"
    })
    assert res.get("ok") is False
    assert res.get("status") == "REQUIRE_HUMAN"
    assert "validation humaine" in res.get("reason", "")
    assert "drive.write" in res.get("reason", "")


@pytest.mark.asyncio
async def test_require_human_github_push_intercepted():
    """Vérifie que github.push requiert une validation humaine explicite."""
    reg = CapabilityRegistry()
    res = await reg.execute_capability("github-mcp", {"operation": "push", "branch": "main"})
    assert res.get("ok") is False
    assert res.get("status") == "REQUIRE_HUMAN"
    assert "github.push" in res.get("reason", "")


@pytest.mark.asyncio
async def test_require_human_slack_send_intercepted():
    """Vérifie que slack.send est intercepté en REQUIRE_HUMAN."""
    reg = CapabilityRegistry()
    with patch.object(reg.slack_provider, "send_message", new=AsyncMock()) as mock_slack:
        res = await reg.execute_capability("slack-direct-mcp", {"text": "hello", "channel": "general"})
        assert res.get("ok") is False
        assert res.get("status") == "REQUIRE_HUMAN"
        mock_slack.assert_not_awaited()


@pytest.mark.asyncio
async def test_deny_scope_system_destructive():
    """Vérifie que le scope 'system.destructive' est formellement bloqué en DENY (Fail-Closed)."""
    reg = CapabilityRegistry()
    res = await reg.execute_capability("web-search-mcp", {"query": "test", "scope": "system.destructive"})
    assert res.get("ok") is False
    assert res.get("status") == "DENY"
    assert "POLICY DENY" in res.get("error", "")


@pytest.mark.asyncio
async def test_deny_scope_unknown_action():
    """Vérifie qu'un scope orphelin ou inconnu est rejeté par défaut (Fail-Closed)."""
    reg = CapabilityRegistry()
    res = await reg.execute_capability("web-search-mcp", {"query": "test", "scope": "unauthorized.backdoor"})
    assert res.get("ok") is False
    assert res.get("status") == "DENY"


@pytest.mark.asyncio
async def test_explicit_allow_scope_override():
    """Vérifie qu'un scope valide et inoffensif explicite comme 'code.patch' est respecté."""
    reg = CapabilityRegistry()
    with patch.object(reg.web_provider, "search", new=AsyncMock(return_value={"ok": True})):
        res = await reg.execute_capability("web-search-mcp", {"query": "test", "scope": "code.patch"})
        assert res.get("ok") is True
