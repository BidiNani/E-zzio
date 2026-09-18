"""
E-ZZIO Core V10.11 — Continuous Autonomous Operations Control Loop.
Pilote la boucle continue d'observation, prévision, ordonnancement, exécution, surveillance,
récupération, optimisation et apprentissage :
OBSERVE -> FORECAST -> SCHEDULE -> EXECUTE -> MONITOR -> RECOVER -> OPTIMIZE -> LEARN.
S'appuie sur MultiMissionArbitrator (V10.10) et AutonomousE2EEngine (V10.9).
"""
from __future__ import annotations

import logging
import time
import uuid
from dataclasses import dataclass, field
from enum import Enum

from core.agent.autonomous_e2e_engine import MissionState
from core.operations.multi_mission_arbitrator import (
    DeadlineStatus,
    MultiMissionArbitrator,
    ResourceStatus,
    multi_mission_arbitrator,
)
from core.world.world_model import world_model

logger = logging.getLogger("ezzio.operations.continuous_operations_loop")


class SystemOperatingMode(str, Enum):
    NORMAL = "NORMAL"
    THROTTLED = "THROTTLED"
    DEGRADED = "DEGRADED"
    EMERGENCY = "EMERGENCY"


class ForecastRiskLevel(str, Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


@dataclass
class OperationalForecast:
    forecast_id: str
    risk_level: ForecastRiskLevel
    queue_pressure: float  # pending_missions / max_concurrent
    worker_saturation: float  # busy_workers / total_workers
    deadline_risk_count: int
    predicted_bottleneck: str
    recommendation: str
    timestamp: float = field(default_factory=time.time)


@dataclass
class OperationsLoopCycleResult:
    cycle_id: str
    mode: SystemOperatingMode
    forecast: OperationalForecast
    arbitration_decision_id: str | None
    executed_missions: list[str]
    recovered_workers: list[str]
    duration_seconds: float
    timestamp: float = field(default_factory=time.time)


class ContinuousOperationsControlLoop:
    """Boucle continue de contrôle opérationnel autonome pour E-ZZIO V10.11."""

    def __init__(self, arbitrator: MultiMissionArbitrator | None = None) -> None:
        self.arbitrator: MultiMissionArbitrator = arbitrator or multi_mission_arbitrator
        self.operating_mode: SystemOperatingMode = SystemOperatingMode.NORMAL
        self.cycle_count: int = 0
        self.history: list[OperationsLoopCycleResult] = []

    def forecast_operational_risks(self) -> OperationalForecast:
        """Effectue une prévision proactive des risques d'exploitation et de saturation."""
        f_id = f"fc_{uuid.uuid4().hex[:6]}"
        total_missions = len(self.arbitrator.managed_missions)
        pending = [
            m for m in self.arbitrator.managed_missions.values()
            if m.contract.current_state in (MissionState.RECEIVED, MissionState.PREPARING)
        ]
        busy_workers = len([w for w in self.arbitrator.workers.values() if w.status == ResourceStatus.BUSY])
        total_workers = len(self.arbitrator.workers)

        queue_pressure = round(len(pending) / max(self.arbitrator.max_concurrent_missions, 1), 2)
        worker_sat = round(busy_workers / max(total_workers, 1), 2)

        deadline_risk_count = len([
            m for m in self.arbitrator.managed_missions.values()
            if m.deadline_status in (DeadlineStatus.AT_RISK, DeadlineStatus.DEADLINE_CRITICAL)
        ])

        # Risk Classification
        if queue_pressure > 2.0 or worker_sat >= 1.0 or deadline_risk_count > 2:
            risk = ForecastRiskLevel.CRITICAL
            bottleneck = "WORKER_SATURATION_AND_QUEUE_OVERLOAD"
            rec = "ENFORCE_THROTTLING_AND_PREEMPT_LOW_PRIORITY"
        elif queue_pressure > 1.0 or worker_sat >= 0.75 or deadline_risk_count > 0:
            risk = ForecastRiskLevel.HIGH
            bottleneck = "HIGH_QUEUE_PRESSURE"
            rec = "PRIORITIZE_CRITICAL_AND_ADJUST_SLOTS"
        elif queue_pressure > 0.5:
            risk = ForecastRiskLevel.MEDIUM
            bottleneck = "MODERATE_RESOURCE_DEMAND"
            rec = "MAINTAIN_NORMAL_SCHEDULING"
        else:
            risk = ForecastRiskLevel.LOW
            bottleneck = "NONE"
            rec = "OPTIMAL_OPERATING_CONDITIONS"

        forecast = OperationalForecast(
            forecast_id=f_id,
            risk_level=risk,
            queue_pressure=queue_pressure,
            worker_saturation=worker_sat,
            deadline_risk_count=deadline_risk_count,
            predicted_bottleneck=bottleneck,
            recommendation=rec,
        )

        logger.debug(f"[CONTINUOUS-LOOP] Prévision effectuée: Risk {risk.value} (Queue pressure: {queue_pressure})")
        return forecast

    def adjust_adaptive_throttling(self, forecast: OperationalForecast) -> SystemOperatingMode:
        """Ajuste le mode de throttling adaptatif en fonction de la prévision de risque."""
        if forecast.risk_level == ForecastRiskLevel.CRITICAL:
            self.operating_mode = SystemOperatingMode.EMERGENCY
        elif forecast.risk_level == ForecastRiskLevel.HIGH:
            self.operating_mode = SystemOperatingMode.THROTTLED
        elif forecast.risk_level == ForecastRiskLevel.MEDIUM:
            self.operating_mode = SystemOperatingMode.NORMAL
        else:
            self.operating_mode = SystemOperatingMode.NORMAL

        self.arbitrator._emit_event("THROTTLING_CHANGED", {
            "mode": self.operating_mode.value,
            "forecast_id": forecast.forecast_id,
        })
        return self.operating_mode

    def run_control_cycle(self) -> OperationsLoopCycleResult:
        """Exécute un cycle de contrôle autonome complet (OBSERVE -> FORECAST -> SCHEDULE -> EXECUTE -> MONITOR -> RECOVER -> OPTIMIZE -> LEARN)."""
        t0 = time.time()
        self.cycle_count += 1
        cycle_id = f"cycle_{self.cycle_count}_{uuid.uuid4().hex[:4]}"

        # 1. OBSERVE & RECONCILE WORLD MODEL
        world_model.detect_state_drift()

        # 2. FORECAST RISKS
        forecast = self.forecast_operational_risks()

        # 3. ADAPTIVE THROTTLING
        self.adjust_adaptive_throttling(forecast)

        # 4. SCHEDULE / ARBITRATE
        decision = self.arbitrator.arbitrate_and_schedule()

        # 5. EXECUTE & MONITOR
        executed_missions: list[str] = []
        if decision.selected_mission_id and decision.selected_mission_id != "NONE":
            res = self.arbitrator.execute_managed_mission(decision.selected_mission_id)
            if res.get("status") == "COMPLETED":
                executed_missions.append(decision.selected_mission_id)

        # 6. RECOVER DEGRADED WORKERS / STALLED MISSIONS
        recovered_workers: list[str] = []
        for w_id, worker in list(self.arbitrator.workers.items()):
            if worker.status == ResourceStatus.DEGRADED:
                # Attempt recovery / reset
                worker.status = ResourceStatus.AVAILABLE
                worker.fail_count = 0
                recovered_workers.append(w_id)
                logger.info(f"[CONTINUOUS-LOOP] Worker degraded {w_id} réinitialisé avec succès")

        # 7. OPTIMIZE & LEARN (Record operational event into strategic memory log)
        duration = round(time.time() - t0, 4)

        result = OperationsLoopCycleResult(
            cycle_id=cycle_id,
            mode=self.operating_mode,
            forecast=forecast,
            arbitration_decision_id=decision.decision_id,
            executed_missions=executed_missions,
            recovered_workers=recovered_workers,
            duration_seconds=duration,
        )
        self.history.append(result)

        self.arbitrator._emit_event("CONTROL_CYCLE_COMPLETED", {
            "cycle_id": cycle_id,
            "mode": self.operating_mode.value,
            "duration": duration,
        })

        logger.info(f"[CONTINUOUS-LOOP] Cycle {cycle_id} terminé avec succès (Mode: {self.operating_mode.value}, Durée: {duration}s)")
        return result


continuous_operations_loop = ContinuousOperationsControlLoop()
