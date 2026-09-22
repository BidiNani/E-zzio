"""
Tests unitaires pour la Capability Policy et les connecteurs Google Workspace, GitHub & Web.
"""

from unittest.mock import AsyncMock, Mock, patch

import pytest

from core.capabilities.capability_policy import CapabilityPolicy, PolicyDecision
from core.capabilities.github_provider import GitHubProvider
from core.capabilities.google_workspace_provider import GoogleWorkspaceProvider
from core.capabilities.web_provider import WebProvider


def test_capability_policy_decisions():
    policy = CapabilityPolicy()

    # 1. Scopes Read-Only autorisés (ALLOW)
    dec, msg = policy.evaluate_scope("gmail.read")
    assert dec == PolicyDecision.ALLOW
    assert "POLICY OK" in msg

    dec_drive, _ = policy.evaluate_scope("drive.read")
    assert dec_drive == PolicyDecision.ALLOW

    dec_gh, _ = policy.evaluate_scope("github.read")
    assert dec_gh == PolicyDecision.ALLOW

    dec_web, _ = policy.evaluate_scope("web.search")
    assert dec_web == PolicyDecision.ALLOW

    dec_crawl, _ = policy.evaluate_scope("web.crawl")
    assert dec_crawl == PolicyDecision.ALLOW

    # 2. Scopes mutants avec validation obligatoire (REQUIRE_HUMAN)
    dec_send, msg_send = policy.evaluate_scope("gmail.send", {"target": "user@domain.com"})
    assert dec_send == PolicyDecision.REQUIRE_HUMAN
    assert "REQUIRE_HUMAN" in msg_send

    dec_push, _ = policy.evaluate_scope("github.push")
    assert dec_push == PolicyDecision.REQUIRE_HUMAN

    dec_pr, _ = policy.evaluate_scope("github.pr_create")
    assert dec_pr == PolicyDecision.REQUIRE_HUMAN

    dec_browser, _ = policy.evaluate_scope("browser.automate")
    assert dec_browser == PolicyDecision.REQUIRE_HUMAN

    # 3. Actions interdites (DENY)
    dec_deny, msg_deny = policy.evaluate_scope("system.destructive")
    assert dec_deny == PolicyDecision.DENY


@pytest.mark.asyncio
async def test_google_workspace_provider_read_only():
    workspace = "G:\\AI\\E-zzio"
    provider = GoogleWorkspaceProvider(workspace_root=workspace)

    # Test Gmail list (passe par la policy)
    res_gmail = await provider.list_recent_emails(limit=5)
    assert "ok" in res_gmail
    assert res_gmail["scope"] == "gmail.read"

    # Test Drive list
    res_drive = await provider.list_recent_files(limit=5)
    assert "ok" in res_drive
    assert res_drive["scope"] == "drive.read"

    # Test Calendar list
    res_cal = await provider.list_upcoming_events(limit=5)
    assert "ok" in res_cal
    assert res_cal["scope"] == "calendar.read"


@pytest.mark.asyncio
async def test_github_provider_read_and_mutation_guard():
    workspace = "G:\\AI\\E-zzio"
    gh = GitHubProvider(workspace_root=workspace)

    # Mock du client HTTP : evite tout appel reseau reel (CI sans GITHUB_TOKEN)
    mock_response = Mock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "full_name": "torvalds/linux",
        "description": "Linux kernel source tree",
        "stargazers_count": 185000,
        "default_branch": "master",
        "open_issues_count": 0,
    }
    mock_response.text = ""

    mock_client = AsyncMock()
    mock_client.get.return_value = mock_response

    with patch(
        "core.capabilities.github_provider.get_http_client",
        return_value=mock_client,
    ):
        # 1. Test lecture de métadonnées de repo public (scope: github.read)
        res_info = await gh.get_repo_info("torvalds", "linux")
        assert "ok" in res_info
        assert res_info["ok"] is True
        assert res_info["scope"] == "github.read"
        assert res_info["data"]["name"] == "torvalds/linux"
        assert res_info["data"]["stars"] == 185000

    # 2. Test tentative de création de PR -> Interception REQUIRE_HUMAN
    #    (pas d'appel HTTP : la policy intercepte avant)
    res_pr = await gh.create_pull_request(
        owner="BidiNani",
        repo="E-zzio",
        title="Test PR auto-générée",
        head="feature/test",
        base="main"
    )
    assert res_pr["ok"] is False
    assert res_pr["status"] == "REQUIRE_HUMAN"
    assert "draft_pr" in res_pr


@pytest.mark.asyncio
async def test_web_provider_search_and_crawl():
    web = WebProvider()

    # 1. Test HTML to Markdown
    sample_html = "<html><body><h1>Titre Test</h1><p>Paragraphe important.</p><li>Item 1</li></body></html>"
    md = web._html_to_markdown(sample_html)
    assert "# Titre Test" in md
    assert "Paragraphe important." in md
    assert "- Item 1" in md

    # 2. Test search policy evaluation
    res_search = await web.search("Python documentation", limit=3)
    assert "ok" in res_search
    assert res_search["scope"] == "web.search"
