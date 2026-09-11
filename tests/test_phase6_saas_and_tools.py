"""
Phase 6 Test Suite — Validation des capacités SaaS externes (Google Workspace, GitHub, Web Search) sous CapabilityPolicy.
"""

import pytest
from core.capabilities.capability_policy import CapabilityPolicy, PolicyDecision


def test_phase6_google_workspace_read_only_policy():
    """Vérifie que les connecteurs Google Workspace / GitHub sont confinés en lecture seule."""
    policy = CapabilityPolicy()

    # Lecture emails / calendrier -> ALLOW
    dec_mail, _ = policy.evaluate_scope("gmail.read")
    assert dec_mail == PolicyDecision.ALLOW

    dec_gh, _ = policy.evaluate_scope("github.read")
    assert dec_gh == PolicyDecision.ALLOW

    # Mutation / Envoi d'email ou Push de commit -> REQUIRE_HUMAN
    dec_send, _ = policy.evaluate_scope("gmail.send", {"target": "test@example.com"})
    assert dec_send == PolicyDecision.REQUIRE_HUMAN

    dec_push, _ = policy.evaluate_scope("github.push", {"branch": "main"})
    assert dec_push == PolicyDecision.REQUIRE_HUMAN


def test_phase6_web_search_anti_ssrf_governance():
    """Vérifie que la recherche web est gouvernée et ne permet aucune fuite SSRF."""
    from core.perception.safe_fetcher import SafeWebFetcher, SSRFSecurityError
    fetcher = SafeWebFetcher()
    with pytest.raises(SSRFSecurityError):
        fetcher.validate_url_safety("http://127.0.0.1:9090/secret")
