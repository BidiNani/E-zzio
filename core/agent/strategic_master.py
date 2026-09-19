"""
E-ZZIO Core V10.5 — Strategic Master Engine for Long-Horizon Planning & Governed Scheduling.
Pilote la hiérarchie des objectifs persistants (Goals -> Programs -> Projects -> Missions),
l'ordonnancement multi-modes (Immediate, Scheduled, Recurring, Event-Triggered), l'anticipation de risques et l'arbitrage.
"""
from __future__ import annotations

import logging
import time
import uuid
from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any

logger = logging.getLogger("ezzio.agent.strategic_master")


class GoalStatus(StrEnum):
    PLANNED = "PLANNED"
    ACTIVE = "ACTIVE"
    PAUSED = "PAUSED"
    BLOCKED = "BLOCKED"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"
    ARCHIVED = "ARCHIVED"


class GoalPriority(StrEnum):
    CRITICAL = "CRITICAL"
    HIGH = "HIGH"
    NORMAL = "NORMAL"
    LOW = "LOW"
    BACKGROUND = "BACKGROUND"


class SchedulingMode(StrEnum):
    IMMEDIATE = "IMMEDIATE"
    DEFERRED = "DEFERRED"
    SCHEDULED = "SCHEDULED"
    RECURRING = "RECURRING"
    DEPENDENCY_TRIGGERED = "DEPENDENCY_TRIGGERED"
    CONDITION_TRIGGERED = "CONDITION_TRIGGERED"


@dataclass
class StrategicGoal:
    goal_id: str
    title: str
    description: str
    priority: GoalPriority = GoalPriority.NORMAL
    status: GoalStatus = GoalStatus.PLANNED
    deadline: float | None = None
    parent_goal_id: str | None = None
    children_ids: list[str] = field(default_factory=list)
    dependencies: list[str] = field(default_factory=list)
    progress: float = 0.0  # 0.0 à 100.0
    checkpoints: list[dict[str, Any]] = field(default_factory=list)
    success_criteria: list[str] = field(default_factory=list)
    budget: float = 100.0
    budget_used: float = 0.0
    deduplication_key: str | None = None
    created_at: float = field(default_factory=time.time)
    updated_at: float = field(default_factory=time.time)


@dataclass
class ScheduledTask:
    task_id: str
    goal_id: str
    mission_id: str | None = None
    mode: SchedulingMode = SchedulingMode.IMMEDIATE
    cron_pattern: str | None = None
    trigger_condition: str | None = None
    status: str = "PENDING"  # PENDING, RUNNING, COMPLETED, FAILED
    next_run: float = field(default_factory=time.time)
    execution_count: int = 0
    deduplication_key: str | None = None


@dataclass
class RiskForecast:
    forecast_id: str
    goal_id: str
    risk_type: str
    probability: float
    impact: str
    preventive_action: str


class StrategicMasterEngine:
    """Moteur souverain de planification stratégique long-terme d'E-ZZIO."""

    def __init__(self) -> None:
        self.goals: dict[str, StrategicGoal] = {}
        self.scheduled_tasks: dict[str, ScheduledTask] = {}
        self.executed_dedup_keys: set[str] = set()
        self.risk_forecasts: dict[str, RiskForecast] = {}
        self._is_active: bool = True

    def create_goal(
        self,
        title: str,
        description: str,
        priority: GoalPriority = GoalPriority.NORMAL,
        deadline: float | None = None,
        parent_goal_id: str | None = None,
        dependencies: list[str] | None = None,
        budget: float = 100.0,
        success_criteria: list[str] | None = None,
        deduplication_key: str | None = None,
    ) -> StrategicGoal:
        """Crée et enregistre un objectif persistant au sein du Strategic Master."""
        if deduplication_key and deduplication_key in self.executed_dedup_keys:
            # Idempotence: retourne l'objectif existant
            for g in self.goals.values():
                if g.deduplication_key == deduplication_key:
                    return g

        goal_id = f"goal_{uuid.uuid4().hex[:8]}"
        goal = StrategicGoal(
            goal_id=goal_id,
            title=title,
            description=description,
            priority=priority,
            deadline=deadline,
            parent_goal_id=parent_goal_id,
            dependencies=dependencies or [],
            budget=budget,
            success_criteria=success_criteria or [],
            deduplication_key=deduplication_key,
        )
        self.goals[goal_id] = goal

        if parent_goal_id and parent_goal_id in self.goals:
            self.goals[parent_goal_id].children_ids.append(goal_id)

        if deduplication_key:
            self.executed_dedup_keys.add(deduplication_key)

        logger.info(f"[STRATEGIC-MASTER] Goal créé: {goal_id} ({title})")
        return goal

    def schedule_task(
        self,
        goal_id: str,
        mode: SchedulingMode = SchedulingMode.IMMEDIATE,
        cron_pattern: str | None = None,
        trigger_condition: str | None = None,
        deduplication_key: str | None = None,
    ) -> ScheduledTask:
        """Planifie l'exécution d'une tâche sous gouvernance du Scheduler."""
        if deduplication_key and deduplication_key in self.executed_dedup_keys:
            for t in self.scheduled_tasks.values():
                if t.deduplication_key == deduplication_key:
                    return t

        task_id = f"task_{uuid.uuid4().hex[:8]}"
        task = ScheduledTask(
            task_id=task_id,
            goal_id=goal_id,
            mode=mode,
            cron_pattern=cron_pattern,
            trigger_condition=trigger_condition,
            deduplication_key=deduplication_key,
        )
        self.scheduled_tasks[task_id] = task

        if deduplication_key:
            self.executed_dedup_keys.add(deduplication_key)

        logger.info(f"[STRATEGIC-MASTER] Task planifiée: {task_id} pour goal {goal_id} ({mode.value})")
        return task

    def evaluate_progress(self, goal_id: str) -> float:
        """Calcule dynamiquement le taux de progression réel d'un objectif."""
        goal = self.goals.get(goal_id)
        if not goal:
            return 0.0

        if not goal.children_ids:
            return goal.progress

        children_progress = [self.evaluate_progress(cid) for cid in goal.children_ids]
        avg_progress = sum(children_progress) / len(children_progress)
        goal.progress = round(avg_progress, 1)
        if goal.progress >= 100.0:
            goal.status = GoalStatus.COMPLETED
        return goal.progress

    def forecast_risks(self, goal_id: str) -> list[RiskForecast]:
        """Analyse prédictive des risques d'échéances et de dépendances."""
        goal = self.goals.get(goal_id)
        if not goal:
            return []

        forecasts = []
        now = time.time()

        # 1. Vérification du risque de deadline
        if goal.deadline and goal.deadline < now + 3600 and goal.progress < 50.0:
            f = RiskForecast(
                forecast_id=f"rf_{uuid.uuid4().hex[:6]}",
                goal_id=goal_id,
                risk_type="DEADLINE_MISS",
                probability=0.85,
                impact="HIGH",
                preventive_action="Assign additional QA/Coder worker and elevate priority to CRITICAL",
            )
            forecasts.append(f)
            self.risk_forecasts[f.forecast_id] = f

        # 2. Vérification des dépendances bloquées
        for dep_id in goal.dependencies:
            dep_goal = self.goals.get(dep_id)
            if dep_goal and dep_goal.status in (GoalStatus.BLOCKED, GoalStatus.FAILED):
                f = RiskForecast(
                    forecast_id=f"rf_{uuid.uuid4().hex[:6]}",
                    goal_id=goal_id,
                    risk_type="DEPENDENCY_BLOCKED",
                    probability=1.0,
                    impact="CRITICAL",
                    preventive_action=f"Replan goal {goal_id} to resolve dependency {dep_id}",
                )
                forecasts.append(f)
                self.risk_forecasts[f.forecast_id] = f

        return forecasts

    def simulate_what_if(self, goal_id: str, hypothetical_change: str) -> dict[str, Any]:
        """Simule l'impact d'une réallocation de ressources sans altérer l'état réel."""
        goal = self.goals.get(goal_id)
        if not goal:
            return {"error": "Goal not found"}

        return {
            "simulation": True,
            "goal_id": goal_id,
            "hypothetical_change": hypothetical_change,
            "estimated_completion_delta_hours": -2.5 if "add worker" in hypothetical_change.lower() else +1.0,
            "estimated_risk": "LOW" if "add worker" in hypothetical_change.lower() else "MEDIUM",
        }

    def replan_goal(self, goal_id: str, reason: str) -> bool:
        """Replanification autonome suite à un échec ou un blocage de dépendance."""
        goal = self.goals.get(goal_id)
        if not goal:
            return False

        goal.status = GoalStatus.ACTIVE
        goal.checkpoints.append({
            "timestamp": time.time(),
            "event": "REPLANNED",
            "reason": reason,
        })
        logger.info(f"[STRATEGIC-MASTER] Replanning effectué pour {goal_id}: {reason}")
        return True

    def cancel_goal_tree(self, root_goal_id: str, reason: str) -> list[str]:
        """Kill Switch: annule proprement un objectif et toute sa sous-arborescence."""
        cancelled = []
        queue = [root_goal_id]

        while queue:
            curr_id = queue.pop(0)
            g = self.goals.get(curr_id)
            if not g:
                continue

            g.status = GoalStatus.CANCELLED
            g.updated_at = time.time()
            cancelled.append(curr_id)
            queue.extend(g.children_ids)

        logger.warning(f"[KILL-SWITCH] Arborescence de Goals annulée depuis '{root_goal_id}': {cancelled}")
        return cancelled


strategic_master = StrategicMasterEngine()
