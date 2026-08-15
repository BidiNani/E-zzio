"""
E-ZZIO V7.34 — Evolution Scorer
Attribue un score d'utilité et de viabilité à l'évolution en fonction de son impact.
"""
from core.evolution_intelligence.impact_analyzer import impact_analyzer

class EvolutionScorer:
    def compute_score(self, content: str, expected_benefit: float = 0.8) -> dict:
        metrics = impact_analyzer.analyze_impact(content)
        
        # Formule de score : Bénéfice attendu pondéré par le risque de régression et la complexité
        penalty = (metrics["complexity_score"] * 0.3) + (metrics["regression_probability"] * 0.5)
        evolution_score = max(0.0, round(expected_benefit - penalty, 2))

        # Décision de promotion intelligente (Seuil fixé à 0.5)
        approved = evolution_score >= 0.5

        return {
            "evolution_score": evolution_score,
            "metrics": metrics,
            "promotion_recommended": approved,
            "reason": "SCORE_THRESHOLD_MET" if approved else "SCORE_TOO_LOW_OR_HIGH_RISK"
        }

evolution_scorer = EvolutionScorer()
