"""
E-ZZIO Test Suite — Priority 4 Capability Qualification & Execution.
Certifie contractuellement les 5 capacités qualifiées / candidates :
1. web-search-mcp (Moteur de recherche web sous contrôle SSRF)
2. crawl4ai-engine (Moteur d'extraction web sous limite de charge et SSRF)
3. github-mcp (Connecteur GitHub auto-hébergé avec scopes stricts)
4. google-workspace-mcp (Connecteur Google Workspace avec scopes lecture stricts)
5. glm-5.3-candidate (Candidat LLM sous statut CANDIDATE / Fail-Closed)
"""
import pytest
from core.capabilities.registry import CapabilityRegistry
from core.capabilities.capability_qualification import QualificationStatus


@pytest.mark.asyncio
async def test_priority_4_web_search_mcp_qualification():
    reg = CapabilityRegistry()
    qual = reg.get_qualification("web-search-mcp")
    assert qual is not None
    assert qual.status == QualificationStatus.QUALIFIED
    assert qual.category == "web"
    assert qual.fail_closed is True
    assert qual.ssrf_protection is True


@pytest.mark.asyncio
async def test_priority_4_crawl4ai_engine_qualification():
    reg = CapabilityRegistry()
    qual = reg.get_qualification("crawl4ai-engine")
    assert qual is not None
    assert qual.status == QualificationStatus.QUALIFIED
    assert qual.category == "web"
    assert qual.max_payload_mb == 10.0


@pytest.mark.asyncio
async def test_priority_4_github_and_google_mcp_qualification():
    reg = CapabilityRegistry()

    gh_qual = reg.get_qualification("github-mcp")
    assert gh_qual is not None
    assert gh_qual.status == QualificationStatus.QUALIFIED
    assert "GITHUB_TOKEN" in gh_qual.secrets_required

    gw_qual = reg.get_qualification("google-workspace-mcp")
    assert gw_qual is not None
    assert gw_qual.status == QualificationStatus.QUALIFIED
    assert "gmail.readonly" in gw_qual.permissions


@pytest.mark.asyncio
async def test_priority_4_glm_candidate_fail_closed():
    reg = CapabilityRegistry()
    glm_qual = reg.get_qualification("glm-5.3-candidate")
    assert glm_qual is not None
    assert glm_qual.status == QualificationStatus.CANDIDATE

    # En statut CANDIDATE, l'exécution directe en production est bloquée (Fail-Closed)
    res = await reg.execute_capability("glm-5.3-candidate", {"messages": [{"role": "user", "content": "hello"}]})
    assert res["ok"] is False
    assert "CANDIDATE : exécution interdite" in res["error"]


@pytest.mark.asyncio
async def test_priority_4_execute_web_capabilities_safely():
    reg = CapabilityRegistry()

    # SSRF protection sur URL privée
    crawl_res = await reg.execute_capability("crawl4ai-engine", {"url": "http://169.254.169.254/latest/meta-data"})
    assert crawl_res["ok"] is False
    assert "[SSRF-PROTECT]" in crawl_res["error"]


@pytest.mark.asyncio
async def test_direct_slack_provider_require_human():
    from core.capabilities.slack_provider import SlackProvider
    slack = SlackProvider()
    res = await slack.send_message(text="Deploy update", channel="#general")
    assert res["ok"] is False
    assert res["requires_human"] is True
    assert res["status"] == "PENDING_APPROVAL"
    assert "slack.send" in res["reason"]

