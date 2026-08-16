from pathlib import Path
from runtime.governance.decision import DecisionContract
from runtime.governance.risk import RiskEngine
from runtime.governance.rollback import RollbackManager
from runtime.governance.governance_ledger import GovernanceLedger

class GovernanceGate:
    def __init__(self, root_dir: Path, autonomy_budget: float = 100.0):
        self.root_dir = root_dir
        self.budget = autonomy_budget
        self.ledger = GovernanceLedger(root_dir / "runtime" / "governance" / "ledger.jsonl")

    def evaluate(self, decision: DecisionContract) -> dict:
        """Machine d'état du Gatekeeper : Schema -> Signature -> Risk -> Budget -> Rollback -> Approved/Denied"""
        
        # 1. Enregistrement de la requête
        self.ledger.log_event("ACTION_REQUESTED", decision.decision_id, {"action": decision.action, "target": decision.target})

        # 2. Vérification de la signature / intégrité
        if not decision.verify_integrity():
            self.ledger.log_event("ACTION_REJECTED", decision.decision_id, {"reason": "DECISION_SPOOF_DETECTED"})
            return {"status": "DENIED", "reason": "Invalid signature / Decision Spoof"}

        # 3. Calcul objectif du risque
        calculated_risk = RiskEngine.calculate_risk(decision.action, decision.target, decision.resource_cost)
        if calculated_risk > 0.8:
            self.ledger.log_event("ACTION_REJECTED", decision.decision_id, {"reason": "RISK_THRESHOLD_EXCEEDED", "risk": calculated_risk})
            return {"status": "DENIED", "reason": f"Risk score too high: {calculated_risk}"}

        # 4. Vérification du budget d'autonomie
        action_cost = decision.resource_cost.get("cost_units", 10)
        if self.budget < action_cost:
            self.ledger.log_event("ACTION_REJECTED", decision.decision_id, {"reason": "AUTONOMY_BUDGET_EXHAUSTED", "budget": self.budget})
            return {"status": "DENIED", "reason": "Autonomy budget exhausted"}

        # 5. Préparation du Rollback si requis
        snapshot = None
        if decision.rollback_required:
            snapshot = RollbackManager.create_snapshot(decision.target, self.root_dir)

        # 6. Approbation finale
        self.budget -= action_cost
        self.ledger.log_event("ACTION_APPROVED", decision.decision_id, {"remaining_budget": self.budget})
        
        return {
            "status": "APPROVED",
            "permission_token": f"TOKEN-{decision.decision_id}-GRANT",
            "rollback_manifest": snapshot
        }
