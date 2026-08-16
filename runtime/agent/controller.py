import time
from runtime.tools.parser import ToolParser
from runtime.core.microkernel import RuntimeBuilder
from runtime.audit.logger import AuditLogger
from runtime.memory.semantic.vector_store import VectorStore

class AgentController:
    """Pilote la boucle cognitive et communique avec le MicroKernel en intégrant la mémoire sémantique."""
    def __init__(self, router, context_builder, max_steps: int = 4):
        self.router = router
        self.context_builder = context_builder
        self.runtime = RuntimeBuilder().with_allowed_level(0).build()
        self.auditor = AuditLogger()
        self.max_steps = max_steps
        self.vector_store = VectorStore()

    def run_loop(self, initial_user_query: str, memory, profile: str = "production") -> str:
        step_count = 0
        thought_history = []
        current_tool_output = None
        session_id = getattr(memory, "session_id", "unknown_session")

        # 1. Retrieval sémantique en amont (Contexte enrichi par la mémoire)
        semantic_hints = []
        try:
            # Si un embedder est disponible ou via une requête texte directe
            embedder_func = getattr(memory, "embed_text", None)
            if embedder_func:
                vector = embedder_func(initial_user_query)
                if vector:
                    semantic_hints = self.vector_store.search(vector)
        except Exception:
            pass

        # Injection optionnelle des indices sémantiques dans l'historique initial
        if semantic_hints:
            thought_history.append({
                "step": 0, 
                "type": "semantic_memory_retrieval", 
                "hints": semantic_hints
            })

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

            success_flag = (tool_result.get("success") if isinstance(tool_result, dict) else getattr(tool_result, "success", None))
            self.auditor.log_agent_action(session_id, step_count, request.name, success_flag, duration)

            if success_flag:
                thought_history.append({"step": step_count, "tool": request.name, "status": "success"})
                current_tool_output = (tool_result.get("output") if isinstance(tool_result, dict) else getattr(tool_result, "output", None))
                
                # 2. Apprentissage épisodique en aval (Stockage du succès si pertinent)
                try:
                    store_func = getattr(memory, "embed_text", None)
                    if store_func:
                        vec = store_func(initial_user_query)
                        if vec:
                            self.vector_store.add(f"session_{session_id}_{step_count}", vec, f"Query: {initial_user_query} | Tool: {request.name} -> SUCCESS")
                except Exception:
                    pass

                continue
            else:
                error_msg = (tool_result.get('error') if isinstance(tool_result, dict) else getattr(tool_result, 'error', None))
                return f"❌ [Action interrompue] {error_msg}"

        return "❌ Erreur critique : Boucle agentique interrompue."