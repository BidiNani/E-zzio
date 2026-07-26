import time
import uuid
import importlib
from typing import Dict, Any, Callable, Optional, List
from runtime.action.contracts import ActionContract
from runtime.action.store import ActionStore

class ActionRegistry:
    """Dynamic registry supporting persistence, execution ledger, and automatic bootstrap hydration."""
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
            handler_ref=contract.handler_ref,
            cost=contract.cost,
            timeout=contract.timeout,
            schema=contract.schema
        )

    def bootstrap(self, handler_resolver: Optional[Callable[[str], Callable]] = None) -> int:
        """
        Recharge les contrats depuis SQLite et résout leurs handlers pour restaurer l'état du registre au démarrage.
        """
        raw_contracts = self.store.load_contracts()
        loaded_count = 0

        for rc in raw_contracts:
            contract = ActionContract(
                name=rc["name"],
                description=rc["description"],
                permission=rc["permission"],
                handler_ref=rc["handler_ref"],
                cost=rc["cost"],
                timeout=rc["timeout"],
                schema=rc["schema"]
            )
            self._contracts[contract.name] = contract
            
            # Résolution du handler
            handler = None
            if handler_resolver and contract.handler_ref:
                handler = handler_resolver(contract.handler_ref)
            elif contract.handler_ref:
                handler = self._default_resolver(contract.handler_ref)

            if handler:
                self._handlers[contract.name] = handler
                loaded_count += 1

        return loaded_count

    def _default_resolver(self, handler_ref: str) -> Optional[Callable]:
        """Résout dynamiquement une référence textuelle (ex: 'module.sub:func') via importlib."""
        try:
            if ":" in handler_ref:
                mod_name, func_name = handler_ref.split(":")
            else:
                parts = handler_ref.split(".")
                mod_name, func_name = ".".join(parts[:-1]), parts[-1]
            
            mod = importlib.import_module(mod_name)
            return getattr(mod, func_name)
        except Exception as e:
            print(f"[!] Erreur de résolution du handler '{handler_ref}': {e}")
            return None

    def get_contract(self, name: str) -> Optional[ActionContract]:
        return self._contracts.get(name)

    def execute(self, name: str, payload: Dict[str, Any], active_permissions: Optional[List[str]] = None) -> Dict[str, Any]:
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
