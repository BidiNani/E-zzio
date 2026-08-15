"""
E-ZZIO V7.24.4 — Scoring Engine (Hardened)
Applique des variations de score marquées selon l'état réel de la RAM,
du cache local et de la pression système.
"""
from core.routing.contracts import RouteConstraints

class RoutingScorer:
    @staticmethod
    def calculate_final_score(
        capability_match: float,
        health_status: float,
        reliability: float,
        latency_score: float,
        cost_score: float,
        confidence: float,
        constraints: RouteConstraints,
        is_local: bool = False,
        is_loaded_in_ram: bool = False,
        high_ram_pressure: bool = False
    ) -> float:
        # 1. Base score pondéré (Total max = 1.0)
        base_score = (
            (capability_match * 0.35) +
            (health_status * 0.25) +
            (reliability * 0.20) +
            (latency_score * 0.10) +
            (cost_score * 0.10)
        )

        # 2. Lissage par la confiance (Cold Start)
        confidence_multiplier = 0.5 + (0.5 * confidence)
        real_score = base_score * confidence_multiplier

        # 3. Application des modificateurs d'état matériel (Ollama Governor)
        if is_local:
            if is_loaded_in_ram:
                real_score += 0.08  # Bonus "Modèle Chaud" (zéro latence de chargement)
            else:
                real_score -= 0.18  # Pénalité "Modèle Froid" (coût de swap)
                
            if high_ram_pressure:
                real_score -= 0.40  # Pénalité critique de saturation RAM (>80% de 10Go) -> Force le Cloud

        return max(0.05, round(real_score, 3))
