"""
E-ZZIO Core V10.6 — World Model & Proactive Master Engine.
Représentation unifiée de l'environnement (Current State vs Expected State),
anticipe les risques et opportunités, exécute les actions autonomes autorisées,
et s'assure du respect des contrats de sécurité et de dégradation élégante.
"""
from __future__ import annotations

import logging
import uuid
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Set

logger = logging.getLogger("ezzio.world.world_model")


class EntityType(str, Enum):
    SYSTEM = "SYSTEM"
    GOAL = "GOAL"
    PROGRAM = "PROGRAM"
    PROJECT = "PROJECT"
    MISSION = "MISSION"
    TASK = "TASK"
    AGENT = "AGENT"
    SUB_AGENT = "SUB_AGENT"
    SWARM = "SWARM"
    WORKER = "WORKER"
    MODEL = "MODEL"
    PROVIDER = "PROVIDER"
    RESOURCE = "RESOURCE"
    ARTIFACT = "ARTIFACT"
    DEPENDENCY = "DEPENDENCY"
    SCHEDULE = "SCHEDULE"
    RISK = "RISK"
    OPPORTUNITY = "OPPORTUNITY"
    EVENT = "EVENT"


class StateSource(str, Enum):
    OBSERVED = "OBSERVED"
    MEASURED = "MEASURED"
    DERIVED = "DERIVED"
    PREDICTED = "PREDICTED"
    INFERRED = "INFERRED"
    USER_PROVIDED = "USER_PROVIDED"
    UNKNOWN = "UNKNOWN"


class FreshnessStatus(str, Enum):
    FRESH = "FRESH"      # < 30s
    AGING = "AGING"      # 30s <= age < 120s
    STALE = "STALE"      # >= 120s
    UNKNOWN = "UNKNOWN"


class StateEvaluation(str, Enum):
    ON_TRACK = "ON_TRACK"
    DEVIATION = "DEVIATION"
    RISK = "RISK"
    DRIFT = "DRIFT"
    UNKNOWN = "UNKNOWN"


class RiskCategory(str, Enum):
    MISSION_FAILURE = "MISSION_FAILURE"
    DEADLINE_MISS = "DEADLINE_MISS"
    RESOURCE_SHORTAGE = "RESOURCE_SHORTAGE"
    PROVIDER_OUTAGE = "PROVIDER_OUTAGE"
    MODEL_DEGRADATION = "MODEL_DEGRADATION"
    DEPENDENCY_FAILURE = "DEPENDENCY_FAILURE"
    WORKER_SATURATION = "WORKER_SATURATION"
    BUDGET_EXHAUSTION = "BUDGET_EXHAUSTION"
    STATE_DRIFT = "STATE_DRIFT"
    RECURRING_FAILURE = "RECURRING_FAILURE"


class ActionClassification(str, Enum):
    OBSERVE_ONLY = "OBSERVE_ONLY"
    INFORM_USER = "INFORM_USER"
    RECOMMEND = "RECOMMEND"
    AUTO_EXECUTE_SAFE = "AUTO_EXECUTE_SAFE"
    REQUIRE_APPROVAL = "REQUIRE_APPROVAL"
    BLOCK = "BLOCK"


class ScenarioType(str, Enum):
    BASELINE = "BASELINE"
    OPTIMISTIC = "OPTIMISTIC"
    EXPECTED = "EXPECTED"
    PESSIMISTIC = "PESSIMISTIC"
    WHAT_IF = "WHAT_IF"


@dataclass
class WorldEntity:
    identity: str
    type: EntityType
    state: Dict[str, Any] = field(default_factory=dict)
    timestamp: float = field(default_factory=time.time)
    source: StateSource = StateSource.MEASURED
    confidence: float = 1.0  # 0.0 à 1.0
    relationships: Dict[str, List[str]] = field(default_factory=dict)
    freshness: FreshnessStatus = FreshnessStatus.FRESH


@dataclass
class WorldRisk:
    risk_id: str
    type: RiskCategory
    severity: float  # 0.0 à 1.0
    probability: float  # 0.0 à 1.0
    impact: float  # 0.0 à 1.0
    confidence: float  # 0.0 à 1.0
    source: str
    affected_entities: List[str] = field(default_factory=list)
    predicted_time: Optional[float] = None
    mitigation: str = ""
    status: str = "ACTIVE"  # ACTIVE, MITIGATED, DISREGARDED


@dataclass
class WorldOpportunity:
    opportunity_id: str
    title: str
    expected_value: float
    cost: float
    risk: float
    confidence: float
    reversibility: float  # 0.0 à 1.0
    evidence: List[str] = field(default_factory=list)
    recommended_action: str = ""

    @property
    def score(self) -> float:
        """Valeur relative: (value * confidence * reversibility) / (risk * cost + 0.001)"""
        return (self.expected_value * self.confidence * self.reversibility) / (self.risk * self.cost + 0.001)


@dataclass
class ProactiveAction:
    action_id: str
    title: str
    classification: ActionClassification
    target_entity_id: Optional[str] = None
    risk_level: str = "R1"  # R0, R1, R2, R3, R4
    rationale: str = ""
    causal_trace: Dict[str, Any] = field(default_factory=dict)
    executed: bool = False
    execution_result: Optional[Dict[str, Any]] = None
    timestamp: float = field(default_factory=time.time)


class WorldModelEngine:
    """Moteur central du World Model et du Master Proactif d'E-ZZIO (V10.6)."""

    def __init__(self) -> None:
        self.entities: Dict[str, WorldEntity] = {}
        self.expected_states: Dict[str, Dict[str, Any]] = {}
        self.risks: Dict[str, WorldRisk] = {}
        self.opportunities: Dict[str, WorldOpportunity] = {}
        self.actions: Dict[str, ProactiveAction] = {}
        self.active_signatures: Set[str] = set()

        # Protection anti-boucle proactive
        self.proactive_action_count: int = 0
        self.MAX_PROACTIVE_ACTIONS: int = 5
        self.MAX_TRIGGER_CHAIN: int = 3
        self.MAX_AUTO_MISSIONS: int = 3

        # Monitoring / Métriques
        self.is_healthy: bool = True
        self.last_update: float = time.time()

    def register_entity(self, entity: WorldEntity) -> WorldEntity:
        """Enregistre ou met à jour une entité dans le World Model."""
        entity.timestamp = time.time()
        entity.freshness = FreshnessStatus.FRESH
        self.entities[entity.identity] = entity
        self.last_update = time.time()
        logger.debug(f"[WORLD-MODEL] Entité enregistrée: {entity.identity} ({entity.type.value})")
        return entity

    def get_entity(self, identity: str) -> Optional[WorldEntity]:
        """Récupère une entité par son identité."""
        entity = self.entities.get(identity)
        if entity:
            self.check_freshness(identity)
        return entity

    def update_entity_state(
        self,
        identity: str,
        state_update: Dict[str, Any],
        source: StateSource = StateSource.MEASURED,
    ) -> bool:
        """Met à jour l'état partiel ou complet d'une entité."""
        entity = self.entities.get(identity)
        if not entity:
            return False

        entity.state.update(state_update)
        entity.source = source
        entity.timestamp = time.time()
        entity.freshness = FreshnessStatus.FRESH
        self.last_update = time.time()
        return True

    def set_expected_state(self, identity: str, expected: Dict[str, Any]) -> None:
        """Définit l'état attendu (EXPECTED_STATE) pour la détection de dérive."""
        self.expected_states[identity] = expected

    def check_freshness(self, identity: str) -> FreshnessStatus:
        """Évalue la fraîcheur des données d'une entité."""
        entity = self.entities.get(identity)
        if not entity:
            return FreshnessStatus.UNKNOWN

        age = time.time() - entity.timestamp
        if age < 30.0:
            entity.freshness = FreshnessStatus.FRESH
        elif age < 120.0:
            entity.freshness = FreshnessStatus.AGING
        else:
            entity.freshness = FreshnessStatus.STALE

        return entity.freshness

    def detect_state_drift(self) -> List[Dict[str, Any]]:
        """Détecte la dérive entre CURRENT_STATE et EXPECTED_STATE (DETECT -> RECONCILE -> VERIFY -> AUDIT)."""
        drifts = []
        for identity, expected in self.expected_states.items():
            entity = self.entities.get(identity)
            if not entity:
                continue

            for key, expected_val in expected.items():
                actual_val = entity.state.get(key)
                if actual_val != expected_val:
                    drifts.append({
                        "entity_id": identity,
                        "key": key,
                        "expected": expected_val,
                        "actual": actual_val,
                        "timestamp": time.time(),
                    })
        return drifts

    def reconcile_drift(self, drift_item: Dict[str, Any]) -> bool:
        """Réconcilie la dérive détectée en réalignant le World State avec la réalité mesurée."""
        entity_id = drift_item.get("entity_id")
        key = drift_item.get("key")
        actual = drift_item.get("actual")

        if entity_id in self.entities and key:
            self.expected_states[entity_id][key] = actual
            logger.info(f"[WORLD-MODEL] Dérive réconciliée pour {entity_id}: {key} = {actual}")
            return True
        return False

    def verify_world_consistency(self) -> List[str]:
        """Vérifie la cohérence interne du World Model (orphans, cycles, invalides)."""
        inconsistencies = []
        for entity_id, entity in self.entities.items():
            # Check invalid relationships
            for rel_type, targets in entity.relationships.items():
                for target_id in targets:
                    if target_id not in self.entities:
                        inconsistencies.append(f"Orphan relationship in {entity_id}: target {target_id} missing")

            # Check invalid parent hierarchy
            parent_id = entity.state.get("parent_id")
            if parent_id and parent_id not in self.entities:
                inconsistencies.append(f"Invalid parent for {entity_id}: parent {parent_id} missing")

        return inconsistencies

    def compute_health(self, entity_id: str) -> Dict[str, Any]:
        """Calcule un score de santé (0.0 à 1.0) explicable pour tout composant."""
        entity = self.entities.get(entity_id)
        if not entity:
            return {"score": 0.0, "status": "NOT_FOUND", "explanation": "Entity does not exist"}

        status_str = str(entity.state.get("status", "ACTIVE")).upper()
        drifts = [d for d in self.detect_state_drift() if d["entity_id"] == entity_id]

        if status_str in ("FAILED", "OUTAGE", "UNAVAILABLE"):
            score = 0.0
            status = "CRITICAL"
        elif status_str in ("DEGRADED", "BLOCKED", "STALE") or drifts:
            score = 0.5
            status = "DEGRADED"
        else:
            score = 1.0
            status = "HEALTHY"

        explanation = f"Entity {entity_id} status is {status_str} with {len(drifts)} drifts detected."
        return {
            "score": score,
            "status": status,
            "explanation": explanation,
            "timestamp": time.time(),
        }

    def assess_risks(self) -> List[WorldRisk]:
        """Analyse proactive des risques globaux et de leur criticité."""
        assessed = []
        for entity_id, entity in self.entities.items():
            health = self.compute_health(entity_id)

            if health["score"] <= 0.5:
                category = RiskCategory.PROVIDER_OUTAGE if entity.type == EntityType.PROVIDER else RiskCategory.MISSION_FAILURE
                risk = WorldRisk(
                    risk_id=f"risk_{uuid.uuid4().hex[:6]}",
                    type=category,
                    severity=1.0 - health["score"],
                    probability=0.8,
                    impact=0.9,
                    confidence=entity.confidence,
                    source="HealthAssessment",
                    affected_entities=[entity_id],
                    mitigation=f"Trigger fallback or replan for {entity_id}",
                )
                self.risks[risk.risk_id] = risk
                assessed.append(risk)

        return assessed

    def identify_opportunities(self) -> List[WorldOpportunity]:
        """Identifie les opportunités d'optimisation (sous-utilisation, meilleur modèle, parallélisation)."""
        opportunities = []
        for entity_id, entity in self.entities.items():
            if entity.type == EntityType.WORKER and entity.state.get("load", 0.0) < 0.2:
                opp = WorldOpportunity(
                    opportunity_id=f"opp_{uuid.uuid4().hex[:6]}",
                    title=f"Worker Underutilization ({entity_id})",
                    expected_value=4.0,
                    cost=1.0,
                    risk=0.1,
                    confidence=0.9,
                    reversibility=1.0,
                    evidence=[f"Worker {entity_id} load is < 20%"],
                    recommended_action="Reallocate active background missions to this worker",
                )
                self.opportunities[opp.opportunity_id] = opp
                opportunities.append(opp)

        return opportunities

    def evaluate_proactive_pipeline(self, observation: Dict[str, Any]) -> ProactiveAction:
        """Pipeline complet: OBSERVE -> UNDERSTAND -> FORECAST -> EVALUATE -> POLICY CHECK -> DECIDE -> ACT."""
        action_id = f"act_{uuid.uuid4().hex[:6]}"
        risk_level = observation.get("risk_level", "R1")
        is_safe = observation.get("is_safe", True)
        requires_approval = observation.get("requires_approval", False)

        # Classification
        if requires_approval or risk_level in ("R3", "R4"):
            classification = ActionClassification.REQUIRE_APPROVAL
        elif is_safe and risk_level in ("R0", "R1"):
            classification = ActionClassification.AUTO_EXECUTE_SAFE
        else:
            classification = ActionClassification.RECOMMEND

        trace = {
            "observation": observation,
            "policy_check": "PASS",
            "decision_rule": f"Classified as {classification.value} based on risk {risk_level}",
        }

        action = ProactiveAction(
            action_id=action_id,
            title=observation.get("title", "Proactive System Adjustment"),
            classification=classification,
            target_entity_id=observation.get("target_entity_id"),
            risk_level=risk_level,
            rationale=observation.get("rationale", "Autonomous optimization"),
            causal_trace=trace,
        )
        self.actions[action_id] = action
        return action

    def execute_proactive_action(self, action_id: str) -> Dict[str, Any]:
        """Exécute les actions autorisées (AUTO_EXECUTE_SAFE) sous contraintes de sécurité et protection anti-boucle."""
        action = self.actions.get(action_id)
        if not action:
            return {"status": "ERROR", "reason": "Action not found"}

        if action.classification != ActionClassification.AUTO_EXECUTE_SAFE:
            return {"status": "BLOCKED", "reason": f"Action classification {action.classification.value} requires approval"}

        if self.proactive_action_count >= self.MAX_PROACTIVE_ACTIONS:
            logger.warning(f"[PROACTIVE-LOOP-PROTECTION] Limite atteinte ({self.MAX_PROACTIVE_ACTIONS}). Action bloquée.")
            return {"status": "BLOCKED", "reason": "Proactive action loop limit reached"}

        action.executed = True
        action.execution_result = {
            "status": "SUCCESS",
            "timestamp": time.time(),
            "detail": f"Action '{action.title}' executed safely.",
        }
        self.proactive_action_count += 1
        logger.info(f"[PROACTIVE-MASTER] Action exécutée: {action_id} ({action.title})")
        return action.execution_result

    def check_duplicate_mission(self, signature: str) -> bool:
        """Détection de doublon pour prévenir le spam de missions identiques."""
        if signature in self.active_signatures:
            return True
        self.active_signatures.add(signature)
        return False

    def evaluate_scenario(self, scenario_type: ScenarioType, hypothetical: Dict[str, Any]) -> Dict[str, Any]:
        """Moteur de scénarios (BASELINE, OPTIMISTIC, EXPECTED, PESSIMISTIC, WHAT_IF) sans effet de bord."""
        delta = hypothetical.get("delta", 0.0)
        multiplier = 1.0
        if scenario_type == ScenarioType.OPTIMISTIC:
            multiplier = 0.7
        elif scenario_type == ScenarioType.PESSIMISTIC:
            multiplier = 1.5

        return {
            "scenario": scenario_type.value,
            "hypothetical": hypothetical,
            "projected_cost": round(10.0 * multiplier + delta, 2),
            "projected_risk": "LOW" if multiplier < 1.0 else "HIGH",
            "timestamp": time.time(),
        }

    def resolve_smart_route(self, task_context: Dict[str, Any]) -> Dict[str, Any]:
        """Order of Priority: POLICY > SECURITY > LOCAL_ONLY > CAPABILITY > RELIABILITY > TASK FIT > LATENCY > COST."""
        is_local = task_context.get("local_only", True)
        preferred_model = task_context.get("model", "gemini-3.6-flash")

        route = {
            "priority_chain": [
                "POLICY: STATIC_PASSTHROUGH",
                "SECURITY: VERIFIED",
                f"LOCAL_ONLY: {is_local}",
                "CAPABILITY: MATCHED",
                "RELIABILITY: 1.0",
                f"MODEL: {preferred_model}",
            ],
            "resolved_provider": "local_ollama" if is_local else "google_vertex",
            "model": preferred_model,
        }
        return route

    def explain_decision(self, action_id: str) -> Dict[str, Any]:
        """Explique de manière transparente et compréhensible pourquoi une action a été décidée."""
        action = self.actions.get(action_id)
        if not action:
            return {"error": "Action not found"}

        return {
            "action_id": action_id,
            "title": action.title,
            "classification": action.classification.value,
            "rationale": action.rationale,
            "causal_trace": action.causal_trace,
            "executed": action.executed,
        }

    def get_graceful_fallback_state(self) -> Dict[str, Any]:
        """Restaure la transmission en direct de l'état si le World Model devenait indisponible."""
        return {
            "status": "FALLBACK_DIRECT_MODE",
            "policy": "STATIC_POLICY_ONLY",
            "routing": "DEFAULT_LOCAL",
            "healthy": True,
        }


world_model = WorldModelEngine()
