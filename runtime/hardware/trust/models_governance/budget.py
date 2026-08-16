from dataclasses import dataclass
from runtime.hardware.trust.models_governance.model_registry import ModelTrustRegistry
from runtime.hardware.trust.execution.admission.models import ModelIdentity

@dataclass(frozen=True)
class ModelBudgetAllocation:
    model_id: str
    allowed: bool
    granted_workers: int
    granted_ram_mb: int
    reason: str

class ModelBudgetGovernor:
    def __init__(self, trust_registry: ModelTrustRegistry):
        self.trust_registry = trust_registry

    def enforce_budget(self, model_identity: ModelIdentity, requested_workers: int) -> ModelBudgetAllocation:
        """
        Vérifie si le modèle est dans le registre de confiance (non-quarantaine) 
        et applique les budgets stricts de RAM et de workers.
        """
        model_info = self.trust_registry.get_model_status(model_identity.model_id)
        status = model_info.get("status", "QUARANTINE")

        if status == "QUARANTINE":
            return ModelBudgetAllocation(
                model_id=model_identity.model_id,
                allowed=False,
                granted_workers=0,
                granted_ram_mb=0,
                reason="MODEL_IN_QUARANTINE_NOT_TRUSTED"
            )

        max_workers_budget = model_info.get("max_allowed_workers", 4)
        max_ram_budget = model_info.get("max_ram_mb", 4096)

        granted_workers = min(requested_workers, max_workers_budget)

        return ModelBudgetAllocation(
            model_id=model_identity.model_id,
            allowed=True,
            granted_workers=granted_workers,
            granted_ram_mb=max_ram_budget,
            reason="MODEL_BUDGET_ENFORCED_SUCCESSFULLY"
        )
