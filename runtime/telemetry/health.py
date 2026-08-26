from dataclasses import dataclass
from typing import Dict, Any
from runtime.telemetry.collector import TelemetryCollector


@dataclass(frozen=True)
class HealthState:
    status: str
    score: int
    queue_backlog: int
    error_pressure: int
    dropped_metrics: int


class HealthMonitor:
    """Évaluateur de santé composite analysant la latence, les drops et le Backpressure."""

    def __init__(self, collector: TelemetryCollector):
        self.collector = collector

    def evaluate_status(self) -> Dict[str, Any]:
        summary = self.collector.get_summary()

        success_rate = summary.get("success_rate", 1.0)
        p90_latency = summary.get("latency", {}).get("p90", 0.0)
        error_count = sum(summary.get("error_breakdown", {}).values())
        queue_size = summary.get("queue_backlog", 0)
        dropped = summary.get("dropped_metrics", 0)

        # Matrice de calcul du Score Composite (0-100)
        score = 100
        score -= int((1.0 - success_rate) * 100)  # Pénalité directe taux d'échec

        if p90_latency > 1500:
            score -= 25
        elif p90_latency > 500:
            score -= 10

        score -= int(error_count * 1.5)

        # Pénalité Backpressure & Rétention
        if queue_size > 8000:
            score -= 30
        elif queue_size > 5000:
            score -= 15

        score -= dropped * 5  # Pénalité sévère sur la perte de métriques
        score = max(0, min(100, score))

        if score >= 95:
            status = "HEALTHY"
        elif score >= 75:
            status = "DEGRADED"
        elif score >= 50:
            status = "WARNING"
        else:
            status = "CRITICAL"

        state = HealthState(status=status, score=score, queue_backlog=queue_size, error_pressure=error_count, dropped_metrics=dropped)

        return {
            "kernel_health": state.status,
            "health_score": state.score,
            "signals": {
                "success_rate": success_rate,
                "p90_latency_ms": p90_latency,
                "error_pressure": state.error_pressure,
                "io_queue_backlog": state.queue_backlog,
                "dropped_metrics": state.dropped_metrics,
            },
        }
