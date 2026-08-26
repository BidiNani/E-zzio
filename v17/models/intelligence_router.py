from typing import Dict, Any, List, Optional
from pydantic import BaseModel
from v17.models.catalog import REAL_OLLAMA_MODEL_CATALOG, ModelProfile, ModelHealthStatus
from v17.models.performance_store import global_performance_store
from v17.events.buffer import global_event_buffer
from v17.events.models import EventSeverity

class RouteDecision(BaseModel):
    selected_model: str
    provider: str
    confidence: float
    reason: str
    score: float
    alternatives: List[str]
    fallback_model: str
    expected_latency_ms: int
    health_verdict: str

class ModelIntelligenceRouter:
    def __init__(self, catalog: Optional[Dict[str, ModelProfile]] = None):
        self.catalog = catalog or REAL_OLLAMA_MODEL_CATALOG

    def route_for_task(self, task_type: str, context_len: int = 1000, prefer_local: bool = True) -> RouteDecision:
        scored = []
        task_lower = task_type.lower()

        for mid, prof in self.catalog.items():
            if not prof.enabled or prof.health in [ModelHealthStatus.UNAVAILABLE, ModelHealthStatus.QUARANTINED]:
                continue

            # Multi-dimensional score calculation:
            # 1. Capability fit (0.0 - 1.0)
            cap_match = 1.0 if task_lower in [c.lower() for c in prof.capabilities] else 0.2
            
            # Special task matches
            if task_lower in ["powershell", "python", "code"] and "code" in prof.capabilities:
                cap_match = 1.0
            if task_lower in ["fast_reply", "fast_chat"] and "fast_reply" in prof.capabilities:
                cap_match = 1.0
            if task_lower in ["forensic", "reasoning"] and "forensic" in prof.capabilities:
                cap_match = 1.0

            # 2. Quality & Reliability
            quality = prof.quality_score
            reliability = prof.reliability_score

            # 3. Performance history modifier
            stats = global_performance_store.get_model_stats(mid)
            perf_modifier = 0.05 if stats["total"] > 0 and stats["success_rate"] >= 0.95 else 0.0

            # 4. Latency penalty for fast requests
            lat_penalty = 0.2 if (task_lower in ["fast_reply", "fast_chat"] and prof.estimated_latency_ms > 500) else 0.0

            # 5. Local bonus
            local_bonus = 0.25 if (prof.local and prefer_local) else 0.0

            total_score = (cap_match * 0.40) + (quality * 0.25) + (reliability * 0.20) + local_bonus + perf_modifier - lat_penalty
            scored.append((mid, prof, round(total_score, 3)))

        scored.sort(key=lambda x: x[2], reverse=True)

        if not scored:
            prof = list(self.catalog.values())[0]
            return RouteDecision(
                selected_model=prof.model_id,
                provider=prof.provider,
                confidence=0.5,
                reason="Default safe fallback model selected",
                score=0.5,
                alternatives=[],
                fallback_model=prof.model_id,
                expected_latency_ms=prof.estimated_latency_ms,
                health_verdict=prof.health.value
            )

        best_id, best_prof, best_score = scored[0]
        alt_ids = [s[0] for s in scored[1:]]
        fallback_id = alt_ids[0] if alt_ids else best_id

        reason = f"Empirical match for '{task_type}': {best_prof.name} (quality {best_prof.quality_score}, lat {best_prof.estimated_latency_ms}ms) with score {best_score}"

        # Emit V17.2 event
        global_event_buffer.publish(
            event_type="model.selected",
            source="v17.models.intelligence_router",
            payload={
                "task_type": task_type,
                "selected_model": best_id,
                "score": best_score,
                "fallback": fallback_id
            },
            severity=EventSeverity.INFO
        )

        return RouteDecision(
            selected_model=best_id,
            provider=best_prof.provider,
            confidence=min(1.0, best_score),
            reason=reason,
            score=best_score,
            alternatives=alt_ids,
            fallback_model=fallback_id,
            expected_latency_ms=best_prof.estimated_latency_ms,
            health_verdict=best_prof.health.value
        )

    def get_available_models(self) -> List[ModelProfile]:
        return [p for p in self.catalog.values() if p.enabled]

    def get_health_metrics(self) -> Dict[str, str]:
        return {mid: prof.health.value for mid, prof in self.catalog.items()}

model_intelligence_router = ModelIntelligenceRouter()
