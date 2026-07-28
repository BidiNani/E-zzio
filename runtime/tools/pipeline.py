import time
from runtime.tools.parser import ToolParser
from runtime.tools.tool_registry import ToolRegistry
from runtime.audit.logger import AuditLogger
from runtime.security.permissions import SecurityPolicy
from runtime.security.guard import SecurityGuard
from runtime.tools.schema_validator import SchemaValidator
from runtime.tools.tool_schema import ToolResult
from runtime.agent.state_machine import AgentStep
from runtime.agent.result import AgentResult

class AgentPipeline:
    def __init__(self, allowed_runtime_level: int = SecurityPolicy.LEVEL_READ):
        self.registry = ToolRegistry()
        self.auditor = AuditLogger()
        self.allowed_runtime_level = allowed_runtime_level

    def process_llm_output(self, llm_output: str) -> AgentResult:
        request = ToolParser.parse_intent(llm_output)
        if not request:
            self.auditor.log_decision("RESPONSE_NORMAL", {"output_sample": llm_output[:100]})
            return AgentResult(step=AgentStep.RESPONSE, text=llm_output)

        # 1. Validation rigoureuse du schéma d'arguments
        is_valid_schema, schema_error = SchemaValidator.validate(request.name, request.arguments)
        if not is_valid_schema:
            res = ToolResult(success=False, output="", error=f"Erreur de schéma [{request.request_id}] : {schema_error}")
            self.auditor.log_security(f"SchemaValidator a rejeté l'outil {request.name} : {schema_error}", "WARNING")
            return AgentResult(step=AgentStep.ERROR, text=f"❌ [Erreur de schéma ID:{request.request_id}] {schema_error}", tool_request=request, tool_result=res)

        # 2. Contrôle rigoureux via le SecurityGuard
        decision = SecurityGuard.inspect(request.name, self.allowed_runtime_level)
        if not decision.allowed:
            res = ToolResult(success=False, output="", error=f"Action bloquée par SecurityGuard [{request.request_id}] : {decision.reason}")
            self.auditor.log_security(f"SecurityGuard a bloqué {request.name} (ID: {request.request_id}) - Raison: {decision.reason}", "CRITICAL")
            return AgentResult(step=AgentStep.SECURITY_BLOCK, text=f"❌ [Sécurité ID:{request.request_id}] Action bloquée ({decision.reason}).", tool_request=request, tool_result=res)

        # 3. Exécution chronométrée
        start_time = time.time()
        result = self.registry.dispatch(request)
        duration = time.time() - start_time

        self.auditor.log_tool(request, result, duration)
        self.auditor.log_decision("TOOL_EXECUTION", {"tool": request.name, "success": (result.get('success', False) if isinstance(result, dict) else getattr(result, 'success', False)), "id": request.request_id})

        if (result.get('success', False) if isinstance(result, dict) else getattr(result, 'success', False)):
            formatted = f"📂 [Exécution Outil ID:{request.request_id} | {request.name}]\n{(result.get('output', '') if isinstance(result, dict) else getattr(result, 'output', ''))}"
            return AgentResult(step=AgentStep.TOOL_REQUEST, text=formatted, tool_request=request, tool_result=result)
        else:
            formatted = f"❌ [Erreur Outil ID:{request.request_id}] {(result.get("error", "") if isinstance(result, dict) else getattr(result, "error", ""))}"
            return AgentResult(step=AgentStep.ERROR, text=formatted, tool_request=request, tool_result=result)