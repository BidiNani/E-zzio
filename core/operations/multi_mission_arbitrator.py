"""
E-ZZIO Core V10.10 — Multi-Mission Operations Arbitrator & Resource Optimizer.
Gère l'arbitrage, l'ordonnancement, la concurrence, la préemption, la prévention de la famine,
la gouvernance des budgets et la santé opérationnelle de plusieurs missions simultanées.
S'appuie directement sur E-ZZIO Master et AutonomousE2EEngine (V10.9) sans duplication.
"""
from __future__ import annotations

import logging
import uuid
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Set, Tuple

from core.agent.autonomous_e2e_engine import (
    autonomous_e2e_engine,
    AutonomousMissionContract,
    ExecutionCheckpoint,
    MissionState,
    ResultVerificationEngine,
)
from core.agent.self_awareness import self_knowledge
from core.world.world_model import world_model
from core.authority.user_preservation import user_preservation_gate

logger = logging.getLogger("ezzio.operations.multi_mission_arbitrator")


class MissionPriority(str, Enum):
    CRITICAL = "CRITICAL"
    HIGH = "HIGH"
    NORMAL = "NORMAL"
    LOW = "LOW"
    BACKGROUND = "BACKGROUND"


class OperationalHealth(str, Enum):
    HEALTHY = "HEALTHY"
    DEGRADED = "DEGRADED"
    STALLED = "STALLED"
    BLOCKED = "BLOCKED"
    FAILED = "FAILED"
    RECOVERING = "RECOVERING"
    COMPLETED = "COMPLETED"


class ResourceStatus(str, Enum):
    AVAILABLE = "AVAILABLE"
    BUSY = "BUSY"
    RESERVED = "RESERVED"
    DEGRADED = "DEGRADED"
    UNAVAILABLE = "UNAVAILABLE"
    BLOCKED = "BLOCKED"


class DeadlineStatus(str, Enum):
    ON_TRACK = "ON_TRACK"
    AT_RISK = "AT_RISK"
    DEADLINE_CRITICAL = "DEADLINE_CRITICAL"
    OVERDUE = "OVERDUE"


@dataclass
class ManagedWorker:
    worker_id: str
    capabilities: List[str]
    status: ResourceStatus = ResourceStatus.AVAILABLE
    current_mission_id: Optional[str] = None
    last_heartbeat: float = field(default_factory=time.time)
    fail_count: int = 0


@dataclass
class ArbitrationDecision:
    decision_id: str
    selected_mission_id: str
    deferred_mission_ids: List[str]
    preempted_mission_ids: List[str]
    reason: str
    priority_score: float
    timestamp: float = field(default_factory=time.time)


@dataclass
class ManagedMission:
    contract: AutonomousMissionContract
    priority: MissionPriority = MissionPriority.NORMAL
    health: OperationalHealth = OperationalHealth.HEALTHY
    deadline_status: DeadlineStatus = DeadlineStatus.ON_TRACK
    wait_time_seconds: float = 0.0
    dynamic_priority_score: float = 0.0
    preemptible: bool = True
    assigned_worker_ids: List[str] = field(default_factory=list)
    parent_mission_id: Optional[str] = None
    child_mission_ids: List[str] = field(default_factory=list)
    created_at: float = field(default_factory=time.time)


class MultiMissionArbitrator:
    """Arbitre d'opérations multi-missions et optimiseur de ressources pour E-ZZIO V10.10."""

    def __init__(self, max_concurrent_missions: int = 3, total_worker_slots: int = 4) -> None:
        self.managed_missions: Dict[str, ManagedMission] = {}
        self.workers: Dict[str, ManagedWorker] = {}
        self.arbitration_history: List[ArbitrationDecision] = []
        self.event_log: List[Dict[str, Any]] = []

        self.max_concurrent_missions: int = max_concurrent_missions
        self.total_worker_slots: int = total_worker_slots
        self.active_execution_slots: int = 0
        self.fairness_aging_factor: float = 0.1  # Dynamic priority boost per waiting second

        # Instanciation de la flotte de workers par défaut
        self._initialize_worker_pool()

    def _initialize_worker_pool(self) -> None:
        """Initialise le pool de workers managés."""
        for i in range(1, self.total_worker_slots + 1):
            w_id = f"worker_{i}"
            self.workers[w_id] = ManagedWorker(
                worker_id=w_id,
                capabilities=["file_creation", "code_execution", "research", "data_transformation"],
                status=ResourceStatus.AVAILABLE,
            )

    def register_mission(
        self,
        contract: AutonomousMissionContract,
        priority: MissionPriority = MissionPriority.NORMAL,
        preemptible: bool = True,
        parent_mission_id: Optional[str] = None,
    ) -> ManagedMission:
        """Enregistre une nouvelle mission dans le gestionnaire multi-missions."""
        mm = ManagedMission(
            contract=contract,
            priority=priority,
            preemptible=preemptible,
            parent_mission_id=parent_mission_id,
        )
        self.managed_missions[contract.mission_id] = mm

        if parent_mission_id and parent_mission_id in self.managed_missions:
            self.managed_missions[parent_mission_id].child_mission_ids.append(contract.mission_id)

        self._emit_event("MISSION_CREATED", {"mission_id": contract.mission_id, "priority": priority.value})
        logger.info(f"[MULTIMISSION] Mission {contract.mission_id} enregistrée (Priorité: {priority.value})")
        return mm

    def calculate_dynamic_priority(self, mm: ManagedMission) -> float:
        """Calcule le score de priorité dynamique selon la hiérarchie d'arbitrage."""
        base_scores = {
            MissionPriority.CRITICAL: 100.0,
            MissionPriority.HIGH: 75.0,
            MissionPriority.NORMAL: 50.0,
            MissionPriority.LOW: 25.0,
            MissionPriority.BACKGROUND: 10.0,
        }
        score = base_scores.get(mm.priority, 50.0)

        # Risk level weighting
        risk_weights = {"R1": 0.0, "R2": 5.0, "R3": 10.0, "R4": 15.0}
        score += risk_weights.get(mm.contract.risk_level, 0.0)

        # Deadline pressure
        if mm.contract.deadline:
            remaining = mm.contract.deadline - time.time()
            if remaining < 60.0:
                mm.deadline_status = DeadlineStatus.DEADLINE_CRITICAL
                score += 40.0
            elif remaining < 300.0:
                mm.deadline_status = DeadlineStatus.AT_RISK
                score += 20.0
            else:
                mm.deadline_status = DeadlineStatus.ON_TRACK

        # Fairness / Starvation prevention boost
        score += mm.wait_time_seconds * self.fairness_aging_factor

        mm.dynamic_priority_score = round(score, 2)
        return mm.dynamic_priority_score

    def detect_multi_mission_deadlock(self) -> List[str]:
        """Détecte s'il existe une dépendance circulaire ou un blocage de ressources entre missions."""
        deadlocked: List[str] = []
        visited: Set[str] = set()
        rec_stack: Set[str] = set()

        def dfs(m_id: str) -> bool:
            visited.add(m_id)
            rec_stack.add(m_id)

            mm = self.managed_missions.get(m_id)
            if mm:
                for dep_id in mm.contract.dependencies.keys():
                    if dep_id in self.managed_missions:
                        if dep_id not in visited:
                            if dfs(dep_id):
                                return True
                        elif dep_id in rec_stack:
                            return True

            rec_stack.remove(m_id)
            return False

        for m_id in self.managed_missions:
            if m_id not in visited:
                if dfs(m_id):
                    deadlocked.append(m_id)

        if deadlocked:
            logger.warning(f"[MULTIMISSION] Deadlock détecté entre les missions: {deadlocked}")
        return deadlocked

    def arbitrate_and_schedule(self) -> ArbitrationDecision:
        """Arbitre les missions en attente et alloue les ressources disponibles."""
        world_model.detect_state_drift()
        now = time.time()

        # Update wait times
        for mm in self.managed_missions.values():
            if mm.contract.current_state in (MissionState.RECEIVED, MissionState.PLANNING, MissionState.PREPARING):
                mm.wait_time_seconds = now - mm.created_at
            self.calculate_dynamic_priority(mm)

        # Detect deadlocks
        deadlocks = self.detect_multi_mission_deadlock()
        if deadlocks:
            for d_id in deadlocks:
                self.managed_missions[d_id].health = OperationalHealth.BLOCKED
                self._emit_event("MISSION_BLOCKED", {"mission_id": d_id, "reason": "Deadlock detected"})

        # Candidate selection
        pending = [
            mm for mm in self.managed_missions.values()
            if mm.contract.current_state in (MissionState.RECEIVED, MissionState.PREPARING)
            and mm.health != OperationalHealth.BLOCKED
        ]

        pending.sort(key=lambda x: x.dynamic_priority_score, reverse=True)

        if not pending:
            return ArbitrationDecision(
                decision_id=f"dec_{uuid.uuid4().hex[:6]}",
                selected_mission_id="NONE",
                deferred_mission_ids=[],
                preempted_mission_ids=[],
                reason="No pending eligible missions available",
                priority_score=0.0,
            )

        top_candidate = pending[0]
        deferred = [m.contract.mission_id for m in pending[1:]]
        preempted: List[str] = []

        # Check resource availability
        available_workers = [w for w in self.workers.values() if w.status == ResourceStatus.AVAILABLE]

        # Handle Preemption if all slots busy and top candidate is CRITICAL
        if not available_workers and top_candidate.priority in (MissionPriority.CRITICAL, MissionPriority.HIGH):
            # Find running lower priority preemptible mission
            running = [
                m for m in self.managed_missions.values()
                if m.contract.current_state == MissionState.EXECUTING and m.preemptible
            ]
            running.sort(key=lambda x: x.dynamic_priority_score)

            if running and running[0].dynamic_priority_score < top_candidate.dynamic_priority_score:
                victim = running[0]
                self.preempt_mission(victim.contract.mission_id, reason=f"Preempted by higher priority mission {top_candidate.contract.mission_id}")
                preempted.append(victim.contract.mission_id)
                available_workers = [w for w in self.workers.values() if w.status == ResourceStatus.AVAILABLE]

        # Allocate worker
        if available_workers:
            worker = available_workers[0]
            worker.status = ResourceStatus.BUSY
            worker.current_mission_id = top_candidate.contract.mission_id
            top_candidate.assigned_worker_ids = [worker.worker_id]
            top_candidate.contract.current_state = MissionState.EXECUTING

            self._emit_event("MISSION_STARTED", {
                "mission_id": top_candidate.contract.mission_id,
                "worker_id": worker.worker_id,
                "priority_score": top_candidate.dynamic_priority_score,
            })

            reason = f"Allocated worker {worker.worker_id} to mission {top_candidate.contract.mission_id} (Priority score: {top_candidate.dynamic_priority_score})"
        else:
            reason = f"Mission {top_candidate.contract.mission_id} queued; no available worker slots."

        decision = ArbitrationDecision(
            decision_id=f"dec_{uuid.uuid4().hex[:6]}",
            selected_mission_id=top_candidate.contract.mission_id,
            deferred_mission_ids=deferred,
            preempted_mission_ids=preempted,
            reason=reason,
            priority_score=top_candidate.dynamic_priority_score,
        )
        self.arbitration_history.append(decision)
        logger.info(f"[ARBITRATION] {reason}")
        return decision

    def preempt_mission(self, mission_id: str, reason: str = "Preemption requested") -> bool:
        """Préempte de façon sécurisée une mission en cours après création d'un checkpoint."""
        mm = self.managed_missions.get(mission_id)
        if not mm or mm.contract.current_state != MissionState.EXECUTING:
            return False

        # Create checkpoint
        cps = autonomous_e2e_engine.checkpoints.get(mission_id, [])
        step_idx = len(cps)
        autonomous_e2e_engine.create_checkpoint(mission_id, step_idx, completed_nodes=[], pending_nodes=[])

        # Release worker
        for w_id in mm.assigned_worker_ids:
            w = self.workers.get(w_id)
            if w:
                w.status = ResourceStatus.AVAILABLE
                w.current_mission_id = None
        mm.assigned_worker_ids.clear()

        mm.contract.current_state = MissionState.PREPARING  # Ready to resume
        mm.health = OperationalHealth.HEALTHY

        self._emit_event("MISSION_PREEMPTED", {"mission_id": mission_id, "reason": reason})
        logger.info(f"[MULTIMISSION] Mission {mission_id} préemptée avec succès: {reason}")
        return True

    def resume_mission(self, mission_id: str) -> bool:
        """Restaure l'exécution d'une mission préemptée ou interrompue."""
        mm = self.managed_missions.get(mission_id)
        if not mm:
            return False

        cp = autonomous_e2e_engine.resume_from_checkpoint(mission_id)
        if not cp:
            return False

        mm.contract.current_state = MissionState.EXECUTING
        mm.health = OperationalHealth.HEALTHY

        self._emit_event("MISSION_RESUMED", {"mission_id": mission_id, "checkpoint_id": cp.checkpoint_id})
        logger.info(f"[MULTIMISSION] Mission {mission_id} reprise depuis checkpoint {cp.checkpoint_id}")
        return True

    def handle_worker_failure(self, worker_id: str) -> Optional[str]:
        """Gère la défaillance d'un worker en libérant la mission et en la réassignant."""
        worker = self.workers.get(worker_id)
        if not worker:
            return None

        worker.status = ResourceStatus.DEGRADED
        worker.fail_count += 1
        failed_mission_id = worker.current_mission_id

        if failed_mission_id and failed_mission_id in self.managed_missions:
            mm = self.managed_missions[failed_mission_id]
            mm.health = OperationalHealth.RECOVERING
            mm.assigned_worker_ids.remove(worker_id) if worker_id in mm.assigned_worker_ids else None

            # Reallocate alternate worker if available
            alt_workers = [w for w in self.workers.values() if w.status == ResourceStatus.AVAILABLE and w.worker_id != worker_id]
            if alt_workers:
                alt = alt_workers[0]
                alt.status = ResourceStatus.BUSY
                alt.current_mission_id = failed_mission_id
                mm.assigned_worker_ids.append(alt.worker_id)
                mm.health = OperationalHealth.HEALTHY
                logger.info(f"[WORKER-RECOVERY] Substitution réussie: {worker_id} -> {alt.worker_id} pour mission {failed_mission_id}")
            else:
                mm.contract.current_state = MissionState.PREPARING
                logger.warning(f"[WORKER-RECOVERY] Aucun worker alternatif immédiatement disponible pour mission {failed_mission_id}")

        self._emit_event("WORKER_FAILED", {"worker_id": worker_id, "affected_mission": failed_mission_id})
        return failed_mission_id

    def cancel_mission(self, mission_id: str, reason: str = "User/Policy cancellation") -> bool:
        """Annule une mission et propage la cancellation à ses dépendances et sous-missions."""
        mm = self.managed_missions.get(mission_id)
        if not mm:
            return False

        mm.contract.current_state = MissionState.CANCELLED
        mm.health = OperationalHealth.FAILED

        # Release workers
        for w_id in mm.assigned_worker_ids:
            w = self.workers.get(w_id)
            if w:
                w.status = ResourceStatus.AVAILABLE
                w.current_mission_id = None
        mm.assigned_worker_ids.clear()

        # Propagate to child missions
        for child_id in mm.child_mission_ids:
            self.cancel_mission(child_id, reason=f"Parent mission {mission_id} cancelled")

        self._emit_event("MISSION_CANCELLED", {"mission_id": mission_id, "reason": reason})
        logger.info(f"[MULTIMISSION] Mission {mission_id} annulée (Propagation enfant: {len(mm.child_mission_ids)})")
        return True

    def execute_managed_mission(self, mission_id: str) -> Dict[str, Any]:
        """Exécute de façon autonome une mission gérée sous contrôle de l'arbitre multi-missions."""
        mm = self.managed_missions.get(mission_id)
        if not mm:
            return {"status": "ERROR", "reason": "Managed mission not found"}

        # Run via AutonomousE2EEngine
        res = autonomous_e2e_engine.execute_mission_e2e(mission_id)

        if res.get("status") == "COMPLETED":
            mm.contract.current_state = MissionState.COMPLETED
            mm.health = OperationalHealth.COMPLETED

            # Free workers
            for w_id in mm.assigned_worker_ids:
                w = self.workers.get(w_id)
                if w:
                    w.status = ResourceStatus.AVAILABLE
                    w.current_mission_id = None
            mm.assigned_worker_ids.clear()

            self._emit_event("MISSION_COMPLETED", {"mission_id": mission_id})
        elif res.get("status") == "FAILED":
            mm.contract.current_state = MissionState.FAILED
            mm.health = OperationalHealth.FAILED

        return res

    def _emit_event(self, event_type: str, payload: Dict[str, Any]) -> None:
        """Émet un événement auditable sur le bus opérationnel."""
        event = {
            "event_id": f"evt_{uuid.uuid4().hex[:6]}",
            "event_type": event_type,
            "payload": payload,
            "timestamp": time.time(),
        }
        self.event_log.append(event)
        logger.debug(f"[OPERATIONS-EVENT] {event_type}: {payload}")


multi_mission_arbitrator = MultiMissionArbitrator()
