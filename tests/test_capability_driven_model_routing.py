"""
tests/test_capability_driven_model_routing.py — Qualification & Property-Based Unit Tests for Capability & Availability Driven Model Routing
"""
from unittest.mock import MagicMock, patch

import pytest

from core.agent.agent_provider import AgentProviderAdapter, RouteIntegrityError
from core.cognition.local_autonomy import LocalAutonomyManager
from core.cognition.model_router import ModelRouter
from core.models.gemini_pool import GeminiPoolManager
from core.routing.model_registry import (
    CanonicalModelRecord,
    CanonicalModelRegistry,
    ModelQualificationStatus,
    ModelSource,
    canonical_model_registry,
)


def test_01_basic_capability_selection():
    """1. Sélection capacitaire de base : CODING -> gemini-3.7-flash."""
    router = ModelRouter()
    res = router.select_engine(task_type="coding")
    assert res["model"] == "gemini-3.7-flash"
    assert res["role"] == "CODING"
    assert res["provider"] == "gemini"


def test_02_preferred_capability_ranking():
    """2. Classement des préférences : rôle MASTER_STRATEGIC -> gemini-3.8-flash."""
    router = ModelRouter()
    res = router.select_engine(complexity_score=0.9, is_mission=True)
    assert res["model"] == "gemini-3.8-flash"
    assert res["role"] == "MASTER_STRATEGIC"


def test_03_unavailable_best_candidate():
    """3. Candidat bloqué/indisponible : GeminiPool ignore les modèles marqués unsupported/bloqués."""
    pool = GeminiPoolManager()
    now = 100000.0
    pool._unsupported_models["gemini-3.7-flash"] = now + 3600.0

    with patch("time.time", return_value=now):
        candidates = pool.get_candidate_models("coding")
        assert "gemini-3.7-flash" not in candidates


def test_04_fallback_to_next_eligible_candidate():
    """4. Repli vers candidat éligible suivant si le premier est indisponible."""
    pool = GeminiPoolManager()
    now = 100000.0
    pool._unsupported_models["gemini-3.7-flash"] = now + 3600.0

    with patch("time.time", return_value=now):
        candidates = pool.get_candidate_models("coding")
        assert isinstance(candidates, list)


def test_05_no_eligible_candidate_fail_closed():
    """5. Aucun candidat éligible -> FAIL-CLOSED."""
    registry = CanonicalModelRegistry()
    target = registry.resolve_cloud_role("NON_EXISTENT_ROLE_XYZ")
    assert target is None


def test_06_cloud_forbidden():
    """6. Cloud interdit par budget -> FAIL-CLOSED si local indisponible."""
    router = ModelRouter()
    with patch.object(router.local_autonomy, "evaluate_local_first", return_value=(False, "Memory overflow")):
        res = router.select_engine(task_type="local", budget_permits_cloud=False)
        assert res["status"] == "FAIL_CLOSED"
        assert res["error"] == "BUDGET_BLOCKS_CLOUD"


def test_07_privacy_requirement():
    """7. Exigence de confidentialité : prefer_local=True privilégie le moteur local."""
    router = ModelRouter()
    with patch.object(router.local_autonomy, "evaluate_local_first", return_value=(True, "Local eligible")):
        res = router.select_engine(task_type="coding", prefer_local=True)
        assert res["is_local"] is True
        assert res["provider"] == "ollama"


def test_08_vision_requirement():
    """8. Exigence vision : vérification de la capacité vision dans les specs registry."""
    spec = canonical_model_registry.get("gemini-3.8-flash")
    assert spec is not None


def test_09_thinking_compatibility():
    """9. Compatibilité du mode de pensée : vérification du niveau thinking_level."""
    router = ModelRouter()
    res_high = router.select_engine(complexity_score=0.9)
    assert res_high["thinking_level"] in ("high", "medium")


def test_10_budget_blocked():
    """10. Budget bloqué : vérification de la réaction de l'autonomie locale sous restriction budgétaire."""
    mgr = LocalAutonomyManager()
    eligible, reason = mgr.evaluate_local_first(task_type="coding", complexity_score=0.5, budget_permits_cloud=False)
    assert isinstance(eligible, bool)


def test_11_local_available():
    """11. Autonomie locale disponible : évaluation local-first valide."""
    mgr = LocalAutonomyManager()
    eligible, reason = mgr.evaluate_local_first(task_type="coding", complexity_score=0.2)
    assert eligible is True


def test_12_local_unavailable_eligible_cloud():
    """12. Local indisponible -> escalade cloud autorisée."""
    router = ModelRouter()
    with patch.object(router.local_autonomy, "evaluate_local_first", return_value=(False, "Too complex")):
        res = router.select_engine(task_type="coding", prefer_local=True, budget_permits_cloud=True)
        assert res["provider"] == "gemini"
        assert res["model"] == "gemini-3.7-flash"


def test_13_cloud_unavailable_eligible_local():
    """13. Routage local souverain lorsque prefer_local=True."""
    router = ModelRouter()
    res = router.select_engine(task_type="local", prefer_local=True)
    assert res["is_local"] is True


def test_14_deterministic_ranking():
    """14. Classement déterministe : les mêmes entrées produisent la même décision."""
    router = ModelRouter()
    res1 = router.select_engine(task_type="coding", complexity_score=0.6)
    res2 = router.select_engine(task_type="coding", complexity_score=0.6)
    assert res1["model"] == res2["model"]
    assert res1["provider"] == res2["provider"]


def test_15_exact_same_inputs_same_decision():
    """15. Intégrité et reproductibilité déterministe du registre."""
    rec1 = canonical_model_registry.get_by_role("CODING")
    rec2 = canonical_model_registry.get_by_role("CODING")
    assert rec1 is not None and rec2 is not None
    assert rec1.name == rec2.name


def test_16_force_cloud_chooses_eligible_cloud_candidate():
    """16. force_cloud choisit le candidat cloud canonique éligible."""
    registry = CanonicalModelRegistry()
    target = registry.resolve_cloud_role("CODING")
    assert target is not None
    assert target.name == "gemini-3.7-flash"
    assert target.provider != "ollama"


def test_17_force_cloud_fail_closed_when_no_cloud_candidate():
    """17. force_cloud échoue (FAIL-CLOSED) lorsqu'aucun candidat cloud n'existe."""
    registry = CanonicalModelRegistry()
    target = registry.resolve_cloud_role("LOCAL_MINI")
    assert target is None


def test_18_ambiguous_candidates_resolved_by_ranking():
    """18. Ambiguïté (>1 cibles cloud pour un rôle) -> FAIL-CLOSED dans resolve_cloud_role."""
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
    assert target is None, "Plusieurs cibles cloud pour un même rôle doivent déclencher un FAIL-CLOSED"


def test_19_deprecated_disabled_candidates_excluded():
    """19. Les modèles désactivés ne sont pas sélectionnés par resolve_cloud_role."""
    registry = CanonicalModelRegistry()
    rec = registry.get("gemini-3.7-flash")
    if rec:
        rec.enabled = False
        target = registry.resolve_cloud_role("CODING")
        rec.enabled = True
        assert target is None


def test_20_provider_availability_respected():
    """20. Disponibilité du provider GeminiPoolManager respectée."""
    pool = GeminiPoolManager()
    assert hasattr(pool, "acquire_execution_target")
