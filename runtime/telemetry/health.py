from typing import Dict, Any
from runtime.telemetry.collector import TelemetryCollector

class HealthMonitor:
    """Moteur de diagnostic composite calculant le Kernel Health Score (0-100)."""
    
    def __init__(self, collector: TelemetryCollector):
        self.collector = collector

    def evaluate_status(self) -> Dict[str, Any]:
        summary = self.collector.get_summary()
        
        success_rate = summary.get("success_rate", 1.0)
        p90_latency = summary.get("latency", {}).get("p90", 0.0)
        error_count = sum(summary.get("error_breakdown", {}).values())
        queue_size = self.collector.get_queue_size()

        # Construction du Score Composite Base 100
        score = 100
        score -= (1.0 - success_rate) * 100        # Poids massif sur le taux de succès
        
        if p90_latency > 1500: score -= 25         # Latence critique
        elif p90_latency > 500: score -= 10        # Latence dégradée
            
        score -= (error_count * 1.5)               # Pression des erreurs
        
        if queue_size > 5000: score -= 20          # Congestion du sous-système I/O
        
        score = max(0, min(100, int(score)))

        if score >= 95: health = "HEALTHY"
        elif score >= 75: health = "DEGRADED"
        elif score >= 50: health = "WARNING"
        else: health = "CRITICAL"

        return {
            "kernel_health": health,
            "health_score": score,
            "signals": {
                "success_rate": success_rate,
                "p90_latency_ms": p90_latency,
                "error_pressure": error_count,
                "io_queue_size": queue_size
            }
        }
