import time
import uuid
import inspect
import importlib
from typing import Dict, Any, Callable, Optional, List
from runtime.action.contracts import ActionContract
from runtime.action.store import ActionStore
from runtime.action.context import ExecutionContext

class ActionRegistry:
    """Dynamic registry supporting persistence, context inspection, budget enforcement, and execution ledger."""
    def __init__(self, store: Optional[ActionStore] = None):
        self._contracts: Dict[str, ActionContract] = {}
        self._handlers: Dict[str, Callable] = {}
        self.store = store or ActionStore()

    def register(self, contract: ActionContract, handler: Callable):
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

    def _invoke_handler(self, handler: Callable, ctx: ExecutionContext, payload: Dict[str, Any]) -> Any:
        """Inspects signature to support both legacy handler(payload) and v2 handler(ctx, payload)."""
        sig = inspect.signature(handler)
        params = list(sig.parameters.values())
        
        if len(params) == 1:
            return handler(payload)
        return handler(ctx, payload)

    def execute(self, name: str, payload: Dict[str, Any], context: Optional[ExecutionContext] = None) -> Dict[str, Any]:
        exec_id = f"exec_{uuid.uuid4().hex}"
        start_time = time.time()
        contract = self._contracts.get(name)
        cost = contract.cost if contract else 1

        ctx = context or ExecutionContext(
            trace_id=exec_id,
            agent_id="ezzio-core",
            permissions=["*"],
            budget_remaining=100
        )

        if not contract:
            res = {"status": "BLOCKED", "error": f"Unknown action: '{name}'"}
            self.store.log_execution(exec_id, name, "BLOCKED", payload, res, cost, 0.0)
            return res

        # 1. Vérification du Budget
        if ctx.budget_remaining < contract.cost:
            res = {"status": "BLOCKED", "error": f"Insufficient execution budget ({ctx.budget_remaining} < {contract.cost})"}
            self.store.log_execution(exec_id, name, "BLOCKED", payload, res, cost, 0.0)
            return res

        # 2. Vérification des Permissions
        perms = ctx.permissions or []
        if contract.permission != "*" and "*" not in perms and contract.permission not in perms:
            res = {"status": "BLOCKED", "error": f"Permission denied for action '{name}'"}
            self.store.log_execution(exec_id, name, "BLOCKED", payload, res, cost, 0.0)
            return res

        # 3. Validation du Payload
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
            # Consommation du budget
            active_ctx = ctx.consume_budget(contract.cost)
            
            # Invocation sécurisée
            result = self._invoke_handler(handler, active_ctx, payload)
            duration_ms = round((time.time() - start_time) * 1000, 2)
            
            res = {
                "status": "SUCCESS", 
                "result": result, 
                "budget_remaining": active_ctx.budget_remaining
            }
            self.store.log_execution(exec_id, name, "SUCCESS", payload, res, cost, duration_ms)
            return res
        except Exception as e:
            duration_ms = round((time.time() - start_time) * 1000, 2)
            res = {"status": "ERROR", "error": str(e)}
            self.store.log_execution(exec_id, name, "ERROR", payload, res, cost, duration_ms)
            return res
