from runtime.hardware.trust.models.registry import CoreModelRegistry


class PermissionError(Exception):
    """Levée quand une exécution est tentée avec un modèle non conforme ou en quarantaine."""

    pass


class ContractResolver:
    def __init__(self, registry: CoreModelRegistry):
        self.registry = registry

    def resolve_resources(self, model_id: str) -> dict:
        """Résout les limites de ressources allouées à un modèle."""
        contract = self.registry.resolve_contract(model_id)

        if contract.get("trust", {}).get("status") != "TRUSTED":
            raise PermissionError(f"MODEL_NOT_TRUSTED: {model_id}")

        res = contract.get("resources", {})
        return {
            "workers": res.get("max_allowed_workers", 4),
            "ram": res.get("max_ram_mb", 4096),
            "gpu_allowed": res.get("gpu_allowed", False),
        }

    def resolve_security(self, model_id: str) -> dict:
        """Résout les exigences de sécurité pour un modèle donné."""
        contract = self.registry.resolve_contract(model_id)

        if contract.get("trust", {}).get("status") != "TRUSTED":
            raise PermissionError(f"MODEL_NOT_TRUSTED: {model_id}")

        sec = contract.get("security", {})
        return {"attestation_required": sec.get("requires_attestation", True), "ledger_required": sec.get("ledger_required", True)}
