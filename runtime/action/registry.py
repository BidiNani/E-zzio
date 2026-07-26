from typing import Dict, Any, Callable, Optional, List
from runtime.action.contracts import ActionContract

class ActionRegistry:
    """Dynamic registry for action contracts, permissions, and execution handlers."""
    def __init__(self):
        self._contracts: Dict[str, ActionContract] = {}
        self._handlers: Dict[str, Callable[[Dict[str, Any]], Dict[str, Any]]] = {}

    def register(self, contract: ActionContract, handler: Callable[[Dict[str, Any]], Dict[str, Any]]):
        self._contracts[contract.name] = contract
        self._handlers[contract.name] = handler

    def get_contract(self, name: str) -> Optional[ActionContract]:
        return self._contracts.get(name)

    def execute(self, name: str, payload: Dict[str, Any], active_permissions: Optional[List[str]] = None) -> Dict[str, Any]:
        contract = self._contracts.get(name)
        if not contract:
            return {"status": "BLOCKED", "error": f"Unknown action: '{name}'"}

        # Vérification robuste des permissions (support du wildcard '*')
        perms = active_permissions or []
        if contract.permission != "*" and "*" not in perms and contract.permission not in perms:
            return {"status": "BLOCKED", "error": f"Permission denied for action '{name}'. Required: '{contract.permission}'"}

        # Validation du payload via le contrat
        validation_errors = contract.validate_payload(payload)
        if validation_errors:
            return {"status": "BLOCKED", "error": f"Payload validation failed: {validation_errors}"}

        handler = self._handlers.get(name)
        if not handler:
            return {"status": "ERROR", "error": f"No handler registered for action '{name}'"}

        try:
            result = handler(payload)
            return {"status": "SUCCESS", "result": result}
        except Exception as e:
            return {"status": "ERROR", "error": str(e)}
