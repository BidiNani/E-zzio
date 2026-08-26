"""
E-ZZIO V9.1.2 — Opportunity Detector
Transforme les signaux bruts de l'Evolution Observer en opportunités
d'ingénierie structurées et évaluées.
"""

import json
from datetime import datetime, timezone
from runtime.evolution.observer import EvolutionObserver


class OpportunityDetector:
    def __init__(self):
        self.observer = EvolutionObserver()

    def translate_signals_to_opportunities(self) -> list:
        signals = self.observer.scan_environment()
        opportunities = []

        for sig in signals:
            opp = self._map_signal_to_opportunity(sig)
            if opp:
                opportunities.append(opp)

        return opportunities

    def _map_signal_to_opportunity(self, signal: dict) -> dict:
        sig_type = signal.get("type")

        if sig_type == "MISSING_CAPABILITY":
            target = signal.get("target")
            return {
                "opportunity_id": f"OPP-{datetime.now(timezone.utc).strftime('%Y%m%d')}-{target.upper()}",
                "category": "CAPABILITY_EXPANSION",
                "title": f"Installation de la capacité : {target}",
                "description": signal.get("context"),
                "estimated_impact": "HIGH",
                "risk_level": "LOW",
                "target_domain": "skills",
                "recommended_action": f"Générer un plan d'intégration pour le module {target}",
            }

        elif sig_type == "HIGH_FRICTION":
            area = signal.get("area")
            return {
                "opportunity_id": f"OPP-{datetime.now(timezone.utc).strftime('%Y%m%d')}-{area.upper()}",
                "category": "PERFORMANCE_OPTIMIZATION",
                "title": f"Optimisation de la zone : {area}",
                "description": signal.get("context"),
                "estimated_impact": "MEDIUM",
                "risk_level": "LOW",
                "target_domain": "memory_store",
                "recommended_action": f"Planifier un compactage ou un nettoyage ciblé de {area}",
            }

        return None

    def generate_opportunities_report(self) -> dict:
        opps = self.translate_signals_to_opportunities()
        return {
            "mode": "ANALYTICAL_READ_ONLY",
            "timestamp_utc": datetime.now(timezone.utc).isoformat(),
            "total_opportunities_detected": len(opps),
            "opportunities": opps,
            "status": "OPPORTUNITIES_MAPPED",
        }


if __name__ == "__main__":
    detector = OpportunityDetector()
    print(json.dumps(detector.generate_opportunities_report(), indent=2))
