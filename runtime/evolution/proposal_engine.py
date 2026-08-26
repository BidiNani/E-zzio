"""
E-ZZIO V9.1.3 — Proposal Engine
Transforme les opportunités qualifiées en propositions d'évolution formelles
avec plans de rollback, estimation de coûts et traçabilité dans l'Evolution Ledger.
"""

import json
from pathlib import Path
from datetime import datetime, timezone
from runtime.evolution.opportunity_detector import OpportunityDetector

ROOT_DIR = Path(r"G:\AI\E-zzio")
EVOLUTION_LEDGER = ROOT_DIR / "runtime" / "evolution" / "evolution_ledger.jsonl"


class ProposalEngine:
    def __init__(self):
        self.detector = OpportunityDetector()

    def generate_proposals(self) -> list:
        opportunities = self.detector.translate_signals_to_opportunities()
        proposals = []

        for opp in opportunities:
            prop = self._build_formal_proposal(opp)
            if prop:
                proposals.append(prop)
                self._log_to_ledger(prop)

        return proposals

    def _build_formal_proposal(self, opportunity: dict) -> dict:
        opp_id = opportunity.get("opportunity_id")
        date_str = datetime.now(timezone.utc).strftime("%Y%m%d")
        proposal_id = f"EVOL-{date_str}-{opp_id.split('-')[-1]}"

        # Détermination des coûts et du plan de rollback selon la catégorie
        category = opportunity.get("category")
        if category == "CAPABILITY_EXPANSION":
            cost = "Estimated 150MB RAM, 1 new background worker"
            rollback = "Désinstallation du module et suppression du registre de skills associé"
        else:
            cost = "Minimal (<10MB RAM, instantané)"
            rollback = "Restauration du snapshot de travail précédent"

        return {
            "proposal_id": proposal_id,
            "target_opportunity": opp_id,
            "timestamp_utc": datetime.now(timezone.utc).isoformat(),
            "title": opportunity.get("title"),
            "description": opportunity.get("description"),
            "target_domain": opportunity.get("target_domain"),
            "estimated_cost": cost,
            "risk_level": opportunity.get("risk_level"),
            "rollback_plan": rollback,
            "requires_validation": True,
            "status": "PENDING_VALIDATION",
        }

    def _log_to_ledger(self, proposal: dict):
        EVOLUTION_LEDGER.parent.mkdir(parents=True, exist_ok=True)
        with open(EVOLUTION_LEDGER, "a", encoding="utf-8") as f:
            f.write(json.dumps(proposal, ensure_ascii=False) + "\n")

    def generate_proposals_report(self) -> dict:
        proposals = self.generate_proposals()
        return {
            "mode": "GOVERNED_PROPOSAL",
            "timestamp_utc": datetime.now(timezone.utc).isoformat(),
            "total_proposals_generated": len(proposals),
            "proposals": proposals,
            "ledger_path": str(EVOLUTION_LEDGER.relative_to(ROOT_DIR)),
            "status": "PROPOSALS_SEALED",
        }


if __name__ == "__main__":
    engine = ProposalEngine()
    print(json.dumps(engine.generate_proposals_report(), indent=2))
