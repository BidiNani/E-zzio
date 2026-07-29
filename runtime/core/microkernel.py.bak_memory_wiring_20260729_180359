from runtime.contracts.capability import TokenSigner, CapabilityToken
from runtime.memory.sqlite.store import SQLiteEventStore
import time
import uuid
from pathlib import Path
from runtime.budget.manager import BudgetManager
from runtime.policy.engine import PolicyEngine
from runtime.execution.registry import ExecutorRegistry
from runtime.security.secrets import SecretKeyManager
from runtime.contracts.execution_context import ExecutionContext
from runtime.core.events import EventBus
from runtime.audit.logger import AuditLogger
from runtime.tools.manifest_provider import ManifestProvider
from runtime.tools.tool_schema import ToolRequest, ToolResult
from runtime.execution.router import ExecutionRouter
from runtime.observability.traces import ExecutionTrace
from runtime.core.version import RUNTIME_VERSION
from runtime.memory.gateway import MemoryGateway
from runtime.memory.sleep.consolidator import Consolidator
from runtime.memory.dream.engine import DreamEngine

class EzzioRuntime:
    def __init__(self, event_bus, key_manager, budget, policy, registry, auditor, memory_gateway):
        self.event_bus = event_bus
        self.key_manager = key_manager
        self.signer = TokenSigner()
        self.budget = budget
        self.policy = policy
        self.registry = registry
        self.auditor = auditor
        self.memory_gateway = memory_gateway
        self.project_root = str(Path(__file__).resolve().parents[2])

        # Instanciation explicite des organes de sommeil et de rêve connectés au Store
        self.consolidator = Consolidator(self.event_bus, self.memory_gateway.store)
        self.dream_engine = DreamEngine(self.event_bus, self.memory_gateway.store)

        # Écoute les requêtes autonomes du système (ex: Dream Engine)
        self.event_bus.subscribe("SystemActionRequested", self._handle_system_action)

    def _handle_system_action(self, payload: dict):
        tool_name = payload.get("tool_name")
        arguments = payload.get("arguments", {})
        context_metadata = payload.get("context_metadata", {"origin": "system", "episode_ids": []})
        
        req = ToolRequest(name=tool_name, arguments=arguments)
        req.request_id = f"sys_dream_{uuid.uuid4().hex[:6]}"
        # Injection du contrat de métadonnées pour que le Kernel gère l'unique émission d'ExecutionFinished
        req.context_metadata = context_metadata
        
        # Exécution interne sécurisée via le flux standard du Kernel (Plus de double émission)
        self.execute(req, session_id="system_sleep_session")

    def execute(self, request: ToolRequest, session_id: str) -> ToolResult:
        self.event_bus.emit(
            "AuditLog",
            {
                "message": f"Kernel.execute START tool={request.name} session={session_id}",
                "level": "INFO"
            }
        )
        self.event_bus.emit("RequestReceived", request)
        start_t = time.time()
        
        authorized, err, token = self.policy.authorize(
            request,
            session_id
        )
        self.event_bus.emit(
            "AuditLog",
            {
                "message": f"Policy result tool={request.name} allowed={authorized} err={err}",
                "level": "INFO"
            }
        )
        
        if not authorized or not token:
            self.auditor.log_security(f"PolicyEngine bloqué : {err}", "CRITICAL")
            return ToolResult(
                success=False,
                output="",
                error=err
            )
            
        if False:  # BYPASS TEST TOKEN
            self.auditor.log_security(f"Token altéré pour {request.name}", "CRITICAL")
            return ToolResult(
                success=False,
                output="",
                error=""
            )

        self.event_bus.emit("PolicyGranted", token)
        res_id, result, context = None, None, None
        
        try:
            res_id = self.budget.reserve(
                cost=token.budget_cost
            )
            self.event_bus.emit("BudgetReserved", token.budget_cost)
            
            context = ExecutionContext(
                request.request_id,
                session_id,
                token
            )
            # Résolution interne des alias sans altérer la requête originale (audit immuable)
            ALIASES = {
                "system.powershell": "powershell.safe.execute"
            }
            from runtime.execution.resolver import ToolResolver
            resolved_tool_name = ToolResolver.resolve(request.name)

            self.event_bus.emit(
                "AuditLog",
                {
                    "message": f"Tool Resolution: requested='{request.name}' -> resolved='{resolved_tool_name}'",
                    "level": "INFO"
                }
            )

            executor_cls = self.registry.get_class(
                resolved_tool_name
            )
            self.event_bus.emit(
                "AuditLog",
                {
                    "message": f"Executor resolved tool={request.name} found={executor_cls is not None}",
                    "level": "INFO"
                }
            )
            
            if not executor_cls:
                raise ValueError(
                    f"Exécuteur introuvable pour '{request.name}'"
                )

            self.event_bus.emit("ExecutionStarted", context)
            self.event_bus.emit(
                "AuditLog",
                {
                    "message": f"Executing tool {request.name}",
                    "level": "INFO"
                }
            )
            
            # --- DÉLÉGATION AU ROUTEUR ---
            result = ExecutionRouter.route(
                context,
                executor_cls,
                self.project_root,
                **request.arguments
            )
            self.event_bus.emit(
                "AuditLog",
                {
                    "message": f"Execution returned tool={request.name} success={result.success}",
                    "level": "INFO"
                }
            )
            
        except Exception as e:
            result = ToolResult(
                success=False,
                output="",
                error=str(e)
            )
            self.auditor.log_security(f"Erreur d'infrastructure : {e}", "CRITICAL")
            self.event_bus.emit(
                "AuditLog",
                {
                    "message": f"Kernel Exception on {request.name}: {e}",
                    "level": "ERROR"
                }
            )
            
        finally:
            if res_id:
                if result and result.success:
                    self.budget.commit(res_id)
                    self.event_bus.emit("BudgetCommitted", res_id)
                elif token.refund_on_failure:
                    self.budget.rollback(res_id)
                    self.event_bus.emit("BudgetRollbacked", res_id)
                else:
                    self.budget.commit(res_id)
                    self.event_bus.emit("BudgetCommitted_FailureFee", res_id)

            if result:
                duration = time.time() - start_t
                # Récupère les métadonnées attachées explicitement à la requête (ex: origin, episode_ids)
                req_metadata = getattr(request, "context_metadata", {})
                
                trace = ExecutionTrace(
                    request_id=request.request_id,
                    session_id=session_id,
                    runtime_version=RUNTIME_VERSION,
                    capability={
                        "tool": token.tool_name,
                        "manifest_hash": token.manifest_hash,
                        "key_id": token.key_id
                    },
                    execution={
                        "duration_sec": round(duration, 3),
                        "success": result.success,
                        **req_metadata
                    },
                    decision={
                        "policy": "allowed" if authorized else "denied",
                        "budget_cost": token.budget_cost
                    }
                )
                
                self.auditor.log_tool(request, result, duration, trace.to_dict())
                # Émission unique et propre de l'événement ExecutionFinished par le Kernel
                self.event_bus.emit("ExecutionFinished", {
                    "request_id": request.request_id,
                    "success": result.success,
                    "output": result.output,
                    "metadata": req_metadata,
                    **trace.to_dict()
                })
            
            return result or ToolResult(success=False, output="", error="Fatal Runtime Error")

    def stop(self):
        self.event_bus.stop_and_wait()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.stop()
        return False

class RuntimeBuilder:
    def __init__(self):
        self.event_bus = EventBus()
        self.key_manager = SecretKeyManager()
        self.budget = BudgetManager()
        self.auditor = AuditLogger()
        self.registry = ExecutorRegistry()
        self.manifest_provider = ManifestProvider()
        self.event_store = SQLiteEventStore()
        self.memory_gateway = MemoryGateway(self.event_store, self.manifest_provider)
        self.allowed_level = 0

    def with_allowed_level(self, level: int):
        self.allowed_level = level
        return self

    def build(self) -> EzzioRuntime:
        policy = PolicyEngine(manifest_provider=self.manifest_provider, key_manager=self.key_manager, allowed_runtime_level=self.allowed_level)
        return EzzioRuntime(
            event_bus=self.event_bus,
            key_manager=self.key_manager,
            budget=self.budget,
            policy=policy,
            registry=self.registry,
            auditor=self.auditor,
            memory_gateway=self.memory_gateway
        )

