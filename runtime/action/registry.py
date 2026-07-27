import time
import uuid
import inspect
import importlib
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FuturesTimeoutError
from typing import Dict, Any, Callable, Optional, List
from runtime.action.contracts import ActionContract, RiskLevel
from runtime.action.store import ActionStore
from runtime.action.context import ExecutionContext
from runtime.action.state import ExecutionState, validate_transition
from runtime.action.identity import ExecutionIdentity
from runtime.action.resilience import CircuitBreaker

class ActionRegistry:
    """Sovereign Kernel Action Registry enforcing strict cryptographically secured state transitions."""
    def __init__(self, store: Optional[ActionStore] = None):
        self._contracts: Dict[str, ActionContract] = {}
        self._handlers: Dict[str, Callable] = {}
        self._circuit_breakers: Dict[str, CircuitBreaker] = {}
        self.store = store or ActionStore()

    def register(self, contract: ActionContract, handler: Callable):
        self._contracts[contract.name] = contract
        self._handlers[contract.name] = handler
        self._circuit_breakers[contract.name] = CircuitBreaker()
        self.store.save_contract(
            action_id=contract.name.lower(),
            version="1.0",
            name=contract.name,
            description=contract.description,
            permission=contract.permission,
            handler_ref=contract.handler_ref,
            cost=contract.cost,
            timeout=contract.timeout,
            risk_level=contract.risk_level.value if isinstance(contract.risk_level, RiskLevel) else str(contract.risk_level),
            schema=contract.schema
        )

    def bootstrap(self, handler_resolver: Optional[Callable[[str], Callable]] = None) -> int:
        raw_contracts = self.store.load_contracts()
        loaded_count = 0

        for rc in raw_contracts:
            risk = RiskLevel(rc["risk_level"]) if rc["risk_level"] in RiskLevel.__members__ else RiskLevel.LOW
            contract = ActionContract(
                name=rc["name"],
                description=rc["description"],
                permission=rc["permission"],
                handler_ref=rc["handler_ref"],
                cost=rc["cost"],
                timeout=rc["timeout"],
                risk_level=risk,
                schema=rc["schema"]
            )
            self._contracts[contract.name] = contract
            self._circuit_breakers[contract.name] = CircuitBreaker()
            
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
        sig = inspect.signature(handler)
        params = list(sig.parameters.values())
        if len(params) == 1:
            return handler(payload)
        elif len(params) == 2:
            return handler(ctx, payload)
        else:
            raise TypeError(f"Handler signature unsupported: expected 1 or 2 parameters, got {len(params)}.")

    def _transition_to(self, exec_id: str, current: ExecutionState, target: ExecutionState) -> ExecutionState:
        validate_transition(current, target)
        self.store.log_transition(exec_id, current.value, target.value)
        return target

    def execute(self, name: str, payload: Dict[str, Any], context: Optional[ExecutionContext] = None, dry_run: bool = False) -> Dict[str, Any]:
        exec_id = f"exec_{uuid.uuid4().hex}"
        start_time = time.time()
        
        current_state = ExecutionState.CREATED

        contract = self._contracts.get(name)
        cost = contract.cost if contract else 1
        risk_str = contract.risk_level.value if contract and isinstance(contract.risk_level, RiskLevel) else "LOW"

        ctx = context or ExecutionContext(
            trace_id=exec_id,
            agent_id="ezzio-core",
            permissions=("*",),
            budget_remaining=100
        )

        if not ctx.verify_signature():
            current_state = self._transition_to(exec_id, current_state, ExecutionState.QUARANTINED)
            res = {"status": current_state.value, "error": "ExecutionContext signature validation failed! Context tampered."}
            self.store.log_execution(exec_id, name, current_state.value, payload, res, cost, 0.0)
            return res

        current_state = self._transition_to(exec_id, current_state, ExecutionState.VALIDATING)

        if not contract:
            current_state = self._transition_to(exec_id, current_state, ExecutionState.FAILED)
            res = {"status": "BLOCKED", "error": f"Unknown action: '{name}'"}
            self.store.log_execution(exec_id, name, "BLOCKED", payload, res, cost, 0.0)
            return res

        cb = self._circuit_breakers.get(name)
        if cb and not cb.can_execute():
            current_state = self._transition_to(exec_id, current_state, ExecutionState.FAILED)
            res = {"status": "BLOCKED", "error": f"Circuit breaker OPEN for action '{name}'"}
            self.store.log_execution(exec_id, name, "BLOCKED", payload, res, cost, 0.0)
            return res

        if ctx.budget_remaining < contract.cost:
            current_state = self._transition_to(exec_id, current_state, ExecutionState.FAILED)
            res = {"status": "BLOCKED", "error": f"Insufficient execution budget ({ctx.budget_remaining} < {contract.cost})"}
            self.store.log_execution(exec_id, name, "BLOCKED", payload, res, cost, 0.0)
            return res

        perms = ctx.permissions or ()
        if contract.permission != "*" and "*" not in perms and contract.permission not in perms:
            current_state = self._transition_to(exec_id, current_state, ExecutionState.FAILED)
            res = {"status": "BLOCKED", "error": f"Permission denied for action '{name}'"}
            self.store.log_execution(exec_id, name, "BLOCKED", payload, res, cost, 0.0)
            return res

        validation_errors = contract.validate_payload(payload)
        if validation_errors:
            current_state = self._transition_to(exec_id, current_state, ExecutionState.FAILED)
            res = {"status": "BLOCKED", "error": f"Payload validation failed: {validation_errors}"}
            self.store.log_execution(exec_id, name, "BLOCKED", payload, res, cost, 0.0)
            return res

        current_state = self._transition_to(exec_id, current_state, ExecutionState.AUTHORIZED)

        if dry_run:
            current_state = self._transition_to(exec_id, current_state, ExecutionState.SIMULATED)
            res = {
                "status": current_state.value,
                "action": name,
                "required_permission": contract.permission,
                "estimated_cost": contract.cost,
                "risk_level": risk_str
            }
            self.store.log_execution(exec_id, name, current_state.value, payload, res, cost, 0.0)
            return res

        handler = self._handlers.get(name)
        if not handler:
            current_state = self._transition_to(exec_id, current_state, ExecutionState.ERROR)
            res = {"status": current_state.value, "error": f"No handler registered for action '{name}'"}
            self.store.log_execution(exec_id, name, current_state.value, payload, res, cost, 0.0)
            return res

        current_state = self._transition_to(exec_id, current_state, ExecutionState.RUNNING)

        try:
            active_ctx = ctx.consume_budget(contract.cost)
            timeout_seconds = contract.timeout if contract.timeout > 0 else 5.0

            with ThreadPoolExecutor(max_workers=1) as executor:
                future = executor.submit(self._invoke_handler, handler, active_ctx, payload)
                result = future.result(timeout=timeout_seconds)

            duration_ms = round((time.time() - start_time) * 1000, 2)
            current_state = self._transition_to(exec_id, current_state, ExecutionState.SUCCESS)
            if cb: cb.record_success()

            res = {
                "status": current_state.value,
                "result": result,
                "budget_remaining": active_ctx.budget_remaining
            }
            self.store.log_execution(exec_id, name, current_state.value, payload, res, cost, duration_ms)
            self.store.log_evidence(exec_id, ctx.trace_id, name, current_state.value, risk_str, payload, ctx.to_dict(), res, duration_ms)
            return res

        except FuturesTimeoutError:
            duration_ms = round((time.time() - start_time) * 1000, 2)
            current_state = self._transition_to(exec_id, current_state, ExecutionState.TIMEOUT)
            if cb: cb.record_failure()

            res = {"status": current_state.value, "error": f"Action '{name}' timed out after {contract.timeout}s"}
            self.store.log_execution(exec_id, name, current_state.value, payload, res, cost, duration_ms)
            self.store.log_evidence(exec_id, ctx.trace_id, name, current_state.value, risk_str, payload, ctx.to_dict(), res, duration_ms)
            return res

        except TypeError as e:
            duration_ms = round((time.time() - start_time) * 1000, 2)
            current_state = self._transition_to(exec_id, current_state, ExecutionState.ERROR)
            if cb: cb.record_failure()

            res = {
                "status": current_state.value,
                "error": str(e),
                "category": "HANDLER_SIGNATURE_ERROR"
            }
            self.store.log_execution(exec_id, name, current_state.value, payload, res, cost, duration_ms)
            self.store.log_evidence(exec_id, ctx.trace_id, name, current_state.value, risk_str, payload, ctx.to_dict(), res, duration_ms)
            return res

        except Exception as e:
            duration_ms = round((time.time() - start_time) * 1000, 2)
            current_state = self._transition_to(exec_id, current_state, ExecutionState.FAILED)
            if cb: cb.record_failure()

            res = {
                "status": current_state.value,
                "error": str(e),
                "category": "RUNTIME_FAILURE"
            }
            self.store.log_execution(exec_id, name, current_state.value, payload, res, cost, duration_ms)
            self.store.log_evidence(exec_id, ctx.trace_id, name, current_state.value, risk_str, payload, ctx.to_dict(), res, duration_ms)
            return res
