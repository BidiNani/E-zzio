"""
core/cognition/local_autonomy.py — Local Autonomy & Local-First Governance Engine (Phase A11).
Governs local model selection via Ollama and CPU-only execution under ModelRouter authority.
STRICT INVARIANTS:
- No silent cloud fallback: every local unavailability emits an observable LOCAL_UNAVAILABLE event.
- CPU-only policy strictly enforced (no GPU requirements).
- Router remains sole routing authority.
"""
from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from typing import Any

from core.routing.model_registry import ModelSource, canonical_model_registry

logger = logging.getLogger("LocalAutonomy")


@dataclass
class LocalEscalationEvent:
    event_type: str  # "LOCAL_UNAVAILABLE" or "LOCAL_TIMEOUT"
    reason: str
    attempted_model: str
    fallback_model: str
    fallback_provider: str
    timestamp: float = field(default_factory=time.time)

    def to_dict(self) -> dict[str, Any]:
        return {
            "event_type": self.event_type,
            "reason": self.reason,
            "attempted_model": self.attempted_model,
            "fallback_model": self.fallback_model,
            "fallback_provider": self.fallback_provider,
            "timestamp": self.timestamp,
        }


@dataclass
class LocalAutonomyMetrics:
    local_calls: int = 0
    cloud_calls: int = 0
    cloud_calls_avoided: int = 0
    local_latency_ms: float = 0.0
    cloud_latency_ms: float = 0.0
    local_tokens: int = 0
    cloud_tokens: int = 0
    local_failures: int = 0
    escalation_events: list[dict[str, Any]] = field(default_factory=list)

    def get_summary(self) -> dict[str, Any]:
        total_calls = self.local_calls + self.cloud_calls
        local_ratio = (self.local_calls / total_calls) if total_calls > 0 else 0.0
        cloud_ratio = (self.cloud_calls / total_calls) if total_calls > 0 else 0.0
        avg_local_lat = (self.local_latency_ms / self.local_calls) if self.local_calls > 0 else 0.0
        avg_cloud_lat = (self.cloud_latency_ms / self.cloud_calls) if self.cloud_calls > 0 else 0.0
        fallback_rate = (len(self.escalation_events) / total_calls) if total_calls > 0 else 0.0

        return {
            "total_calls": total_calls,
            "local_calls": self.local_calls,
            "cloud_calls": self.cloud_calls,
            "local_call_ratio": round(local_ratio, 4),
            "cloud_call_ratio": round(cloud_ratio, 4),
            "cloud_calls_avoided": self.cloud_calls_avoided,
            "avg_local_latency_ms": round(avg_local_lat, 2),
            "avg_cloud_latency_ms": round(avg_cloud_lat, 2),
            "total_local_tokens": self.local_tokens,
            "total_cloud_tokens": self.cloud_tokens,
            "local_failures": self.local_failures,
            "fallback_rate": round(fallback_rate, 4),
            "escalation_events_count": len(self.escalation_events),
        }


class LocalAutonomyManager:
    """Gère l'inventaire et les métriques de l'autonomie locale sans contourner le Router."""

    def __init__(self, cpu_only: bool = True):
        self.cpu_only = cpu_only
        self.metrics = LocalAutonomyMetrics()
        self._local_available_override: bool | None = None

    def set_local_availability(self, available: bool | None) -> None:
        """Override pour tests ou synchronisation avec probe Ollama."""
        self._local_available_override = available

    def is_local_service_available(self) -> bool:
        if self._local_available_override is not None:
            return self._local_available_override
        # Probe port 11434
        import socket
        try:
            with socket.create_connection(("127.0.0.1", 11434), timeout=0.1):
                return True
        except (TimeoutError, ConnectionRefusedError, OSError):
            return False

    def get_local_inventory(self) -> list[dict[str, Any]]:
        """Inventaire des modèles locaux enregistrés dans le CanonicalModelRegistry."""
        local_models = []
        for model in canonical_model_registry.list_models():
            if model.source == ModelSource.LOCAL or model.provider.lower() in ("ollama", "local"):
                local_models.append({
                    "model_id": model.name,
                    "provider": model.provider,
                    "roles": model.roles,
                    "thinking_level": model.thinking_level,
                    "cpu_only_compatible": self.cpu_only,
                })
        return local_models

    def evaluate_local_first(
        self,
        task_type: str,
        complexity_score: float,
        context_tokens: int = 1000,
        policy_permits_local: bool = True,
        budget_permits_cloud: bool = True,
        max_local_context: int = 32_000,
    ) -> tuple[bool, str]:
        """Évalue si une tâche est éligible au traitement local en priorité."""
        if not policy_permits_local:
            return False, "POLICY_BLOCKS_LOCAL"

        if context_tokens > max_local_context:
            return False, f"CONTEXT_EXCEEDS_LOCAL_LIMIT ({context_tokens} > {max_local_context})"

        if complexity_score > 0.8:
            return False, f"COMPLEXITY_REQUIRES_CLOUD_STRATEGIC ({complexity_score} > 0.8)"

        if not self.is_local_service_available():
            return False, "LOCAL_SERVICE_UNAVAILABLE"

        return True, "LOCAL_FIRST_ELIGIBLE"

    def record_execution(
        self,
        provider: str,
        latency_ms: float = 0.0,
        tokens: int = 0,
        was_local_intended: bool = False,
        escalation_event: LocalEscalationEvent | None = None,
        is_failure: bool = False,
    ) -> None:
        """Enregistre les métriques d'exécution et d'escalade."""
        if provider.lower() in ("local", "ollama"):
            self.metrics.local_calls += 1
            self.metrics.local_latency_ms += latency_ms
            self.metrics.local_tokens += tokens
            if is_failure:
                self.metrics.local_failures += 1
            else:
                self.metrics.cloud_calls_avoided += 1
        else:
            self.metrics.cloud_calls += 1
            self.metrics.cloud_latency_ms += latency_ms
            self.metrics.cloud_tokens += tokens

        if escalation_event:
            self.metrics.escalation_events.append(escalation_event.to_dict())
            logger.warning(
                "[LocalAutonomy] Événement d'escalade observable: %s -> %s (Raison: %s)",
                escalation_event.attempted_model,
                escalation_event.fallback_model,
                escalation_event.reason,
            )
