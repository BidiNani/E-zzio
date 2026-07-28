import time
from runtime.tools.parser import ToolParser
from runtime.core.microkernel import RuntimeBuilder
from runtime.audit.logger import AuditLogger

class AgentController:
    """Pilote la boucle cognitive et communique avec le MicroKernel construit de manière propre."""
    def __init__(self, router, context_builder, max_steps: int = 4):
        self.router = router
        self.context_builder = context_builder
        # Utilisation du Builder
        self.runtime = RuntimeBuilder().with_allowed_level(0).build()
        self.auditor = AuditLogger()
        self.max_steps = max_steps

    def run_loop(self, initial_user_query: str, memory, profile: str = "production") -> str:
        step_count = 0
        thought_history = []
        current_tool_output = None
        session_id = getattr(memory, "session_id", "unknown_session")

        while step_count < self.max_steps:
            step_count += 1
            
            if current_tool_output:
                current_query = f"[TACHE INITIALE] {initial_user_query}\n\n[RÉSULTAT DE L'OUTIL]\n{current_tool_output}\n\n[INSTRUCTION] Analyse et réponds à la tâche initiale."
            else:
                current_query = initial_user_query

            prompt = self.context_builder.build_full_prompt(current_query, memory, profile, thought_history)

            response_obj = self.router.generate(prompt)
            if not response_obj.success:
                return response_obj.text

            llm_raw_text = response_obj.text
            request = ToolParser.parse_intent(llm_raw_text)

            if not request:
                return llm_raw_text

            start_t = time.time()
            tool_result = self.runtime.execute(request, session_id)
            duration = time.time() - start_t

            self.auditor.log_agent_action(session_id, step_count, request.name, (tool_result.get("success") if isinstance(tool_result, dict) else getattr(tool_result, "success", None)), duration)

            if tool_result.success:
                thought_history.append({"step": step_count, "tool": request.name, "status": "success"})
                current_tool_output = (tool_result.get("output") if isinstance(tool_result, dict) else getattr(tool_result, "output", None))
                continue
            else:
                return f"❌ [Action interrompue] {(tool_result.get('error') if isinstance(tool_result, dict) else getattr(tool_result, 'error', None))}"

        return "❌ Erreur critique : Boucle agentique interrompue."