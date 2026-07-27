from typing import Dict, Any
from runtime.telemetry.collector import TelemetryCollector

class HealthMonitor:
    """Analyse les métriques collectées pour générer un diagnostic systémique exploitable par un Agent autonome."""
    
    def __init__(self, collector: TelemetryCollector = None):
        self.collector = collector or TelemetryCollector()

    def evaluate_status(self) -> Dict[str, Any]:
        summary = self.collector.get_summary(persistent=True)
        
        success_rate = summary.get("success_rate", 1.0)
        latency = summary.get("mean_latency_ms", 0.0)
        error_count = sum(summary.get("error_breakdown", {}).values())

        # Calcul d'un Health Score de base 100
        score = 100
        score -= (1.0 - success_rate) * 100  # Pénalité directe sur l'échec
        
        if latency > 1000:
            score -= 20
        elif latency > 500:
            score -= 10
            
        score -= (error_count * 2)  # Pénalité de pression d'erreur
        
        score = max(0, min(100, int(score))) # Clamp 0-100

        if score >= 90:
            health = "HEALTHY"
        elif score >= 70:
            health = "DEGRADED"
        else:
            health = "CRITICAL"

        latency_score = max(0, 100 - int(latency / 20))

        return {
            "kernel_health": health,
            "health_score": score,
            "signals": {
                "success_rate": success_rate,
                "latency_score": latency_score,
                "error_pressure": error_count
            }
        }
