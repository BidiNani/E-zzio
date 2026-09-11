"""E-ZZIO Wave 7 — gouvernance modèle : REJECTED n'exécute jamais."""
import pytest

from core.agent.coder_federation import (
    CoderModelFederationRouter,
    CoderRoutingPlan,
    ProviderCandidate,
    RoutingIntegrityError,
    _normalize_model_name,
)
from core.providers.base_provider import CostClass


def _cand(provider, model):
    return ProviderCandidate(provider_name=provider, model_name=model,
                             cost_class=CostClass.LOCAL, capabilities=[],
                             is_local=True)


def _plan(primary, fallbacks=None):
    return CoderRoutingPlan(primary=primary,
                            fallback_chain=fallbacks or [],
                            profile=None, reason="test", plan_trace={})


def _router():
    return CoderModelFederationRouter(providers={}, audit_ledger=None)


def test_rejected_model_never_executes():
    r = _router()
    plan = _plan(_cand("ollama", "qwen3.5:9b"),
                 [_cand("ollama", "qwen2.5-coder:7b-instruct-q4_K_M")])
    out = r._enforce_model_governance(plan)
    assert out.primary.model_name == "qwen2.5-coder:7b-instruct-q4_K_M"
    assert all("qwen3.5" not in c.model_name
               for c in [out.primary] + out.fallback_chain)


def test_alias_cannot_bypass_registry():
    assert _normalize_model_name("QWEN3.5:9B") == "qwen3.5:9b"
    assert _normalize_model_name("ollama/qwen3.5:9b") == "qwen3.5:9b"
    assert _normalize_model_name("  qwen3.5:9b ") == "qwen3.5:9b"
    r = _router()
    for alias in ("QWEN3.5:9B", "ollama/qwen3.5:9b", "  qwen3.5:9b",
                  "local/qwen3:8b", "DEEPSEEK-R1:8B", "llava:13b"):
        plan = _plan(_cand("ollama", alias),
                     [_cand("ollama", "phi4-mini:latest")])
        out = r._enforce_model_governance(plan)
        assert out.primary.model_name == "phi4-mini:latest", alias


def test_fallback_only_authorized_excludes_rejected():
    r = _router()
    plan = _plan(_cand("ollama", "qwen2.5-coder:7b-instruct-q4_K_M"),
                 [_cand("ollama", "qwen3.5:9b"),
                  _cand("groq", "llama-3.3-70b-versatile")])
    out = r._enforce_model_governance(plan)
    names = [c.model_name for c in [out.primary] + out.fallback_chain]
    assert "qwen3.5:9b" not in names
    assert "llama-3.3-70b-versatile" in names


def test_all_rejected_fail_closed():
    r = _router()
    plan = _plan(_cand("ollama", "qwen3.5:9b"),
                 [_cand("ollama", "qwen3:8b")])
    with pytest.raises(RoutingIntegrityError):
        r._enforce_model_governance(plan)


def test_unknown_flagged_never_silent():
    # Doctrine stricte : UNKNOWN bloqué (BLOCKED), jamais exécuté sous drapeau.
    import pytest
    from core.agent.coder_federation import RoutingIntegrityError
    r = _router()
    seen = []
    r._record_audit = lambda a, p, **k: seen.append((a, p, k.get("status", "SUCCESS")))
    plan = _plan(_cand("openrouter", "qwen/qwen-2.5-coder-32b-instruct"))
    with pytest.raises(RoutingIntegrityError):
        r._enforce_model_governance(plan)
    flags = [a for a, p, s in seen if a == "MODEL_GOVERNANCE_UNKNOWN"]
    assert flags, "UNKNOWN doit être signalé, jamais silencieux"
    assert seen[0][2] == "BLOCKED"
    assert seen[0][1]["blocked"] is True


def test_violation_audited_blocked():
    r = _router()
    seen = []
    r._record_audit = lambda a, p, **k: seen.append((a, p, k.get("status", "SUCCESS")))
    plan = _plan(_cand("ollama", "qwen3.5:9b"),
                 [_cand("gemini", "gemini-3.7-flash")])
    r._enforce_model_governance(plan)
    viol = [(a, p, s) for a, p, s in seen
            if a == "MODEL_GOVERNANCE_VIOLATION"]
    assert viol and viol[0][2] == "BLOCKED"
    assert viol[0][1]["blocked"] is True


def test_selected_vs_actual_divergence_visible():
    from core.observability import metrics as M
    evs = [{"id": 1, "actor": "t", "action": "CODER_MODEL_EXECUTION_SUCCESS",
            "payload": {"successful_provider": "ollama",
                        "successful_model": "qwen2.5-coder",
                        "attempts_count": 2, "fallback_events": [{"a": 1}]},
            "status": "SUCCESS", "timestamp": 1.0}]
    out = M.model_effectiveness(evs)
    assert out["divergences"].value == 1


def test_second_order_rejected_never_calibrates():
    """Chaîne §27 : REJECTED→fallback→worker→metric→calibration impossible."""
    from core.observability import metrics as M
    r = _router()
    plan = _plan(_cand("ollama", "qwen3.5:9b"))
    with pytest.raises(RoutingIntegrityError):
        r._enforce_model_governance(plan)
    out = M.model_effectiveness([])
    assert out["by_model"].n == 0
    assert out["by_model"].status == "UNMEASURED"


def test_dormant_bypass_not_reachable_from_master():
    """§I : L0 Master ne must not transitively load legacy cognitif
    router (app.py/core.api/core.orchestrator) — single routing authority."""
    import sys as _sys
    import core.ezzio_master  # noqa: F401
    assert "core.api" not in _sys.modules
    assert "core.orchestrator" not in _sys.modules


def test_cognitive_router_rejects_legacy_model():
    """§G : cognitive_router ModelRouter (legacy) — REJECTED model
    must never be returned, fail-closed, even in legacy fallback path."""
    from core.cognitive_router import ModelRouter
    router = ModelRouter(gemini_api_key=None)
    for prof in ("prive", "raisonnement", "autonome", "rapide", "inconnu"):
        route = router.resolve_route(prof)
        assert route["primary"]["model"] != "qwen3.5:9b", prof
        assert route["fallback"]["model"] != "qwen3.5:9b", prof
        assert route["primary"]["model"] in {
            "qwen2.5-coder:7b-instruct-q4_K_M", "gemini-3.7-flash"}, prof
        assert route["fallback"]["model"] == "phi4-mini:latest", prof


def test_production_filter_excludes_tests():
    from core.observability import metrics as M
    evs = [{"id": 1, "actor": "t", "action": "MODEL_GOVERNANCE_VIOLATION",
            "payload": {"env": "test"}, "status": "BLOCKED",
            "timestamp": 1.0},
           {"id": 2, "actor": "t", "action": "MODEL_GOVERNANCE_VIOLATION",
            "payload": {"env": "prod"}, "status": "BLOCKED",
            "timestamp": 2.0}]
    assert len(M.prod_only(evs)) == 1
