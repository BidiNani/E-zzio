"""
E-ZZIO Core V10.4 — Strategic Memory & Adaptive Learning Engine.
Mémorise les résultats de mission, la fiabilité réelle des agents, modèles et providers,
les performances d'équipe, les schémas d'échec et les stratégies de récupération sans jamais contourner les règles de sécurité.
"""
from __future__ import annotations

import logging
import math
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional, Set, Tuple

logger = logging.getLogger("ezzio.memory.strategic")


class MissionOutcome(str, Enum):
    SUCCESS = "SUCCESS"
    PARTIAL_SUCCESS = "PARTIAL_SUCCESS"
    FAILED = "FAILED"
    ROLLED_BACK = "ROLLED_BACK"
    CANCELLED = "CANCELLED"
    UNKNOWN = "UNKNOWN"


class MemoryCategory(str, Enum):
    EPISODIC = "EPISODIC"
    SEMANTIC = "SEMANTIC"
    STRATEGIC = "STRATEGIC"
    OPERATIONAL = "OPERATIONAL"


@dataclass
class AgentReliabilityProfile:
    agent_id: str
    tasks_attempted: int = 0
    tasks_completed: int = 0
    tasks_failed: int = 0
    total_latency: float = 0.0
    specialization_scores: Dict[str, float] = field(default_factory=dict)
    confidence: float = 0.0  # 0.0 à 1.0
    last_updated: float = field(default_factory=time.time)

    @property
    def success_rate(self) -> float:
        if self.tasks_attempted == 0:
            return 1.0
        return self.tasks_completed / self.tasks_attempted

    @property
    def average_latency(self) -> float:
        if self.tasks_completed == 0:
            return 0.0
        return self.total_latency / self.tasks_completed


@dataclass
class ModelReliabilityProfile:
    model_id: str
    provider_id: str
    tasks_attempted: int = 0
    tasks_completed: int = 0
    fallback_count: int = 0
    coding_success_count: int = 0
    reasoning_success_count: int = 0
    confidence: float = 0.0

    @property
    def success_rate(self) -> float:
        if self.tasks_attempted == 0:
            return 1.0
        return self.tasks_completed / self.tasks_attempted


@dataclass
class ProviderReliabilityProfile:
    provider_id: str
    tasks_attempted: int = 0
    tasks_completed: int = 0
    total_latency: float = 0.0
    failures_count: int = 0

    @property
    def availability(self) -> float:
        if self.tasks_attempted == 0:
            return 1.0
        return (self.tasks_attempted - self.failures_count) / self.tasks_attempted


@dataclass
class TeamPerformanceProfile:
    team_key: str  # par ex. "CODER+QA+SECURITY"
    missions_count: int = 0
    success_count: int = 0
    total_latency: float = 0.0

    @property
    def success_rate(self) -> float:
        if self.missions_count == 0:
            return 1.0
        return self.success_count / self.missions_count


@dataclass
class FailurePattern:
    pattern_id: str
    category: str
    error_signature: str
    count: int = 1
    best_recovery_strategy: Optional[str] = None


class StrategicMemoryEngine:
    """Moteur souverain d'apprentissage et mémoire stratégique d'E-ZZIO."""

    MIN_SAMPLE_SIZE_FOR_CONFIDENCE = 3

    def __init__(self) -> None:
        self.agent_profiles: Dict[str, AgentReliabilityProfile] = {}
        self.model_profiles: Dict[str, ModelReliabilityProfile] = {}
        self.provider_profiles: Dict[str, ProviderReliabilityProfile] = {}
        self.team_profiles: Dict[str, TeamPerformanceProfile] = {}
        self.failure_patterns: Dict[str, FailurePattern] = {}
        self.exploration_budget: float = 100.0  # budget dédié aux tests d'exploration
        self.exploration_used: float = 0.0
        self._is_available: bool = True

    def record_mission_outcome(
        self,
        mission_id: str,
        outcome: MissionOutcome,
        duration: float,
        cost: float,
        agents_used: List[str],
        model_used: str,
        provider_used: str,
        task_type: str = "CODING",
        error: Optional[str] = None,
        recovery_action: Optional[str] = None,
    ) -> None:
        """Enregistre les résultats réels d'une mission et met à jour les métriques d'apprentissage."""
        if not self._is_available:
            return

        is_success = outcome in (MissionOutcome.SUCCESS, MissionOutcome.PARTIAL_SUCCESS)

        # 1. Mise à jour profil Agents
        for agent_id in set(agents_used):
            prof = self.agent_profiles.setdefault(agent_id, AgentReliabilityProfile(agent_id=agent_id))
            prof.tasks_attempted += 1
            if is_success:
                prof.tasks_completed += 1
                prof.total_latency += duration
                spec_score = prof.specialization_scores.get(task_type, 0.5)
                prof.specialization_scores[task_type] = min(1.0, spec_score + 0.1)
            else:
                prof.tasks_failed += 1
                spec_score = prof.specialization_scores.get(task_type, 0.5)
                prof.specialization_scores[task_type] = max(0.0, spec_score - 0.1)
            # Confiance basée sur la taille d'échantillon
            prof.confidence = min(1.0, prof.tasks_attempted / 10.0)
            prof.last_updated = time.time()

        # 2. Mise à jour profil Modèle
        m_prof = self.model_profiles.setdefault(
            model_used, ModelReliabilityProfile(model_id=model_used, provider_id=provider_used)
        )
        m_prof.tasks_attempted += 1
        if is_success:
            m_prof.tasks_completed += 1
            if task_type == "CODING":
                m_prof.coding_success_count += 1
        m_prof.confidence = min(1.0, m_prof.tasks_attempted / 10.0)

        # 3. Mise à jour profil Provider
        p_prof = self.provider_profiles.setdefault(
            provider_used, ProviderReliabilityProfile(provider_id=provider_used)
        )
        p_prof.tasks_attempted += 1
        if is_success:
            p_prof.tasks_completed += 1
            p_prof.total_latency += duration
        else:
            p_prof.failures_count += 1

        # 4. Mise à jour profil Équipe
        if agents_used:
            team_key = "+".join(sorted(set(agents_used)))
            t_prof = self.team_profiles.setdefault(team_key, TeamPerformanceProfile(team_key=team_key))
            t_prof.missions_count += 1
            if is_success:
                t_prof.success_count += 1
                t_prof.total_latency += duration

        # 5. Détection de Failure Pattern si échec
        if not is_success and error:
            pat_id = f"pat_{hash(error[:50]) & 0xffffff}"
            if pat_id in self.failure_patterns:
                pat = self.failure_patterns[pat_id]
                pat.count += 1
                if recovery_action and is_success:
                    pat.best_recovery_strategy = recovery_action
            else:
                self.failure_patterns[pat_id] = FailurePattern(
                    pattern_id=pat_id,
                    category=task_type,
                    error_signature=error[:100],
                    count=1,
                    best_recovery_strategy=recovery_action,
                )

        logger.info(f"[STRATEGIC-MEMORY] Mission {mission_id} enregistrée: {outcome.value}")

    def recommend_best_team(self, task_type: str) -> List[str]:
        """Propose l'équipe d'agents historiquement la plus efficace."""
        if not self._is_available or not self.team_profiles:
            return ["coder_worker", "qa_tester"]

        # Filtrer par taille d'échantillon minimale
        valid_teams = [t for t in self.team_profiles.values() if t.missions_count >= self.MIN_SAMPLE_SIZE_FOR_CONFIDENCE]
        if not valid_teams:
            return ["coder_worker", "qa_tester"]

        best_team = max(valid_teams, key=lambda t: (t.success_rate, -t.total_latency))
        return best_team.team_key.split("+")

    def recommend_best_provider(self, task_type: str, privacy_required: str = "CLOUD_ALLOWED") -> str:
        """Recommande le provider le plus fiable tout en respectant STRICTEMENT la policy."""
        # 1. Respect absolu de la policy statique (LOCAL_ONLY)
        if privacy_required == "LOCAL_ONLY":
            return "ollama_local"

        if not self._is_available or not self.provider_profiles:
            return "cloud_groq"

        valid_provs = [p for p in self.provider_profiles.values() if p.tasks_attempted >= 1]
        if not valid_provs:
            return "cloud_groq"

        best_prov = max(valid_provs, key=lambda p: (p.availability, -p.failures_count))
        return best_prov.provider_id

    def explain_decision(self, agent_id: str, model_id: str) -> Dict[str, Any]:
        """Fournit une explication transparente et observable sur la recommandation."""
        a_prof = self.agent_profiles.get(agent_id)
        m_prof = self.model_profiles.get(model_id)

        return {
            "agent_id": agent_id,
            "agent_success_rate": round(a_prof.success_rate, 2) if a_prof else 1.0,
            "agent_sample_size": a_prof.tasks_attempted if a_prof else 0,
            "agent_confidence": round(a_prof.confidence, 2) if a_prof else 0.0,
            "model_id": model_id,
            "model_success_rate": round(m_prof.success_rate, 2) if m_prof else 1.0,
            "explanation": f"Recommended based on historical empirical data (agent confidence={a_prof.confidence if a_prof else 0.0}).",
        }

    def set_available(self, available: bool) -> None:
        self._is_available = available


strategic_memory = StrategicMemoryEngine()
