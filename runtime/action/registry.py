import time
import uuid
from typing import Dict, Any, Callable, Optional, List
from runtime.action.contracts import ActionContract
from runtime.action.store import ActionStore

class ActionRegistry:
    """Dynamic registry for action contracts, permissions, handlers, and persistent execution ledger."""
    def __init__(self, store: Optional[ActionStore] = None):
        self._contracts: Dict[str, ActionContract] = {}
        self._handlers: Dict[str, Callable[[Dict[str, Any]], Dict[str, Any]]] = {}
        self.store = store or ActionStore()

    def register(self, contract: ActionContract, handler: Callable[[Dict[str, Any]], Dict[str, Any]]):
        self._contracts[contract.name] = contract
        self._handlers[contract.name] = handler
        self.store.save_contract(
            action_id=contract.name.lower(),
            version="1.0",
            name=contract.name,
            description=contract.description,
            permission=contract.permission,
            cost=contract.cost,
            timeout=contract.timeout,
            schema=contract.schema
        )

    def get_contract(self, name: str) -> Optional[ActionContract]:
        return self._contracts.get(name)

    def execute(self, name: str, payload: Dict[str, Any], active_permissions: Optional[List[str]] = None) -> Dict[str, Any]:
        # UUID complet pour éviter les collisions SQLite
        exec_id = f"exec_{uuid.uuid4().hex}"
        start_time = time.time()
        contract = self._contracts.get(name)
        cost = contract.cost if contract else 1

        if not contract:
            res = {"status": "BLOCKED", "error": f"Unknown action: '{name}'"}
            self.store.log_execution(exec_id, name, "BLOCKED", payload, res, cost, 0.0)
            return res

        perms = active_permissions or []
        if contract.permission != "*" and "*" not in perms and contract.permission not in perms:
            res = {"status": "BLOCKED", "error": f"Permission denied for action '{name}'"}
            self.store.log_execution(exec_id, name, "BLOCKED", payload, res, cost, 0.0)
            return res

        validation_errors = contract.validate_payload(payload)
        if validation_errors:
            res = {"status": "BLOCKED", "error": f"Payload validation failed: {validation_errors}"}
            self.store.log_execution(exec_id, name, "BLOCKED", payload, res, cost, 0.0)
            return res

        handler = self._handlers.get(name)
        if not handler:
            res = {"status": "ERROR", "error": f"No handler registered for action '{name}'"}
            self.store.log_execution(exec_id, name, "ERROR", payload, res, cost, 0.0)
            return res

        try:
            result = handler(payload)
            duration_ms = round((time.time() - start_time) * 1000, 2)
            res = {"status": "SUCCESS", "result": result}
            self.store.log_execution(exec_id, name, "SUCCESS", payload, res, cost, duration_ms)
            return res
        except Exception as e:
            duration_ms = round((time.time() - start_time) * 1000, 2)
            res = {"status": "ERROR", "error": str(e)}
            self.store.log_execution(exec_id, name, "ERROR", payload, res, cost, duration_ms)
            return res
