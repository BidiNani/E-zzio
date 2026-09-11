"""
E-ZZIO Core V10.6 — Test Suite for World Model Engine & Proactive Master.
Valide la représentation d'état, la détection de dérive, l'évaluation de risques/opportunités,
l'exécution d'actions autonomes sécurisées, la protection anti-boucle, et la dégradation élégante.
"""
import pytest
import time
from core.world.world_model import (
    WorldModelEngine,
    WorldEntity,
    EntityType,
    StateSource,
    FreshnessStatus,
    RiskCategory,
    ActionClassification,
    ScenarioType,
)


@pytest.fixture
def world_engine():
    """Fournit une instance propre de WorldModelEngine pour chaque test."""
    return WorldModelEngine()


def test_01_world_entity_registration(world_engine):
    """Vérifie l'enregistrement et le suivi d'une entité du World Model."""
    entity = WorldEntity(
        identity="goal_v10_6_01",
        type=EntityType.GOAL,
        state={"status": "ACTIVE", "progress": 25.0},
        source=StateSource.MEASURED,
    )
    registered = world_engine.register_entity(entity)
    assert registered.identity == "goal_v10_6_01"

    retrieved = world_engine.get_entity("goal_v10_6_01")
    assert retrieved is not None
    assert retrieved.state["progress"] == 25.0
    assert retrieved.freshness == FreshnessStatus.FRESH


def test_02_state_freshness_lifecycle(world_engine):
    """Vérifie la dégradation temporelle de la fraîcheur d'état (FRESH -> AGING -> STALE)."""
    entity = WorldEntity(
        identity="worker_01",
        type=EntityType.WORKER,
        state={"load": 0.1},
        timestamp=time.time() - 150.0,  # 150 secondes dans le passé
    )
    world_engine.register_entity(entity)
    # Remplacer le timestamp par le passé
    world_engine.entities["worker_01"].timestamp = time.time() - 150.0

    status = world_engine.check_freshness("worker_01")
    assert status == FreshnessStatus.STALE


def test_03_state_drift_detection_and_reconciliation(world_engine):
    """Vérifie la détection de dérive entre CURRENT et EXPECTED et sa réconciliation."""
    entity = WorldEntity(
        identity="mission_v10_6_drift",
        type=EntityType.MISSION,
        state={"status": "COMPLETED"},
    )
    world_engine.register_entity(entity)
    world_engine.set_expected_state("mission_v10_6_drift", {"status": "ACTIVE"})

    drifts = world_engine.detect_state_drift()
    assert len(drifts) == 1
    assert drifts[0]["expected"] == "ACTIVE"
    assert drifts[0]["actual"] == "COMPLETED"

    # Réconciliation
    reconciled = world_engine.reconcile_drift(drifts[0])
    assert reconciled is True
    assert len(world_engine.detect_state_drift()) == 0


def test_04_world_consistency_checks(world_engine):
    """Vérifie la détection des entités orphelines et relations invalides."""
    entity = WorldEntity(
        identity="agent_child",
        type=EntityType.AGENT,
        relationships={"depends_on": ["missing_parent_entity"]},
    )
    world_engine.register_entity(entity)

    inconsistencies = world_engine.verify_world_consistency()
    assert len(inconsistencies) > 0
    assert "missing_parent_entity" in inconsistencies[0]


def test_05_health_model_evaluation(world_engine):
    """Vérifie le calcul explicable du score de santé."""
    entity = WorldEntity(
        identity="provider_ollama",
        type=EntityType.PROVIDER,
        state={"status": "DEGRADED"},
    )
    world_engine.register_entity(entity)

    health = world_engine.compute_health("provider_ollama")
    assert health["score"] == 0.5
    assert health["status"] == "DEGRADED"
    assert "provider_ollama" in health["explanation"]


def test_06_risk_and_opportunity_engines(world_engine):
    """Vérifie l'évaluation proactive des risques et opportunités."""
    # Worker sous-utilisé
    worker = WorldEntity(
        identity="worker_idle",
        type=EntityType.WORKER,
        state={"load": 0.05},
    )
    world_engine.register_entity(worker)

    opps = world_engine.identify_opportunities()
    assert len(opps) >= 1
    assert opps[0].score > 0.0
    assert "Worker Underutilization" in opps[0].title


def test_07_proactive_pipeline_and_safety_classification(world_engine):
    """Vérifie la classification des actions (AUTO_EXECUTE_SAFE vs REQUIRE_APPROVAL)."""
    # Safe action
    safe_obs = {"title": "Rebalance Worker Load", "risk_level": "R1", "is_safe": True}
    safe_act = world_engine.evaluate_proactive_pipeline(safe_obs)
    assert safe_act.classification == ActionClassification.AUTO_EXECUTE_SAFE

    # High risk action requiring approval
    risky_obs = {"title": "Delete Archived Database", "risk_level": "R3", "requires_approval": True}
    risky_act = world_engine.evaluate_proactive_pipeline(risky_obs)
    assert risky_act.classification == ActionClassification.REQUIRE_APPROVAL


def test_08_proactive_action_execution_and_loop_protection(world_engine):
    """Vérifie l'exécution des actions autonomes autorisées et la protection anti-boucle."""
    obs = {"title": "Optimize Memory Cache", "risk_level": "R1", "is_safe": True}

    for _ in range( world_engine.MAX_PROACTIVE_ACTIONS + 2):
        act = world_engine.evaluate_proactive_pipeline(obs)
        res = world_engine.execute_proactive_action(act.action_id)

    # La dernière tentative doit être bloquée par la limite anti-boucle
    assert res["status"] == "BLOCKED"
    assert "loop limit reached" in res["reason"]


def test_09_duplicate_prevention(world_engine):
    """Vérifie la détection de signature de mission identique pour éviter les doublons."""
    sig = "mission_signature_v10_6_unique"
    assert world_engine.check_duplicate_mission(sig) is False
    assert world_engine.check_duplicate_mission(sig) is True  # Doublon détecté


def test_10_scenario_engine_what_if(world_engine):
    """Vérifie la simulation de scénarios à blanc (OPTIMISTIC, PESSIMISTIC, WHAT_IF)."""
    scen = world_engine.evaluate_scenario(ScenarioType.OPTIMISTIC, {"delta": -2.0})
    assert scen["scenario"] == "OPTIMISTIC"
    assert scen["projected_cost"] == 5.0
    assert scen["projected_risk"] == "LOW"


def test_11_smart_routing_and_decision_explanation(world_engine):
    """Vérifie la chaîne de priorité de routing et l'explication causale de décision."""
    route = world_engine.resolve_smart_route({"local_only": True, "model": "gemini-3.6-flash"})
    assert route["resolved_provider"] == "local_ollama"
    assert "POLICY: STATIC_PASSTHROUGH" in route["priority_chain"][0]

    obs = {"title": "Scale Worker Fleet", "risk_level": "R1", "is_safe": True, "rationale": "High workload detected"}
    act = world_engine.evaluate_proactive_pipeline(obs)
    exp = world_engine.explain_decision(act.action_id)

    assert exp["title"] == "Scale Worker Fleet"
    assert exp["rationale"] == "High workload detected"


def test_12_graceful_degradation_fallback(world_engine):
    """Vérifie la bascule en mode direct en cas d'indisponibilité du World Model."""
    fallback = world_engine.get_graceful_fallback_state()
    assert fallback["status"] == "FALLBACK_DIRECT_MODE"
    assert fallback["healthy"] is True
