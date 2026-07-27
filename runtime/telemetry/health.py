from typing import Dict, Any
from runtime.telemetry.collector import TelemetryCollector

class HealthMonitor:
    """Analyse les métriques collectées pour déterminer l'état de santé opérationnel."""
    def __init__(self, collector: TelemetryCollector = None):
        self.collector = collector or TelemetryCollector()

    def evaluate_status(self) -> Dict[str, Any]:
        summary = self.collector.get_summary()
        success_rate = summary.get("success_rate", 1.0)

        if success_rate >= 0.95:
            health = "HEALTHY"
        elif success_rate >= 0.80:
            health = "DEGRADED"
        else:
            health = "CRITICAL"

        return {
            "kernel_health": health,
            "metrics": summary
        }
