import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parent.parent))

from runtime.core.message import Message
from runtime.memory.session import WorkingMemory
from runtime.context.builder import ContextBuilder
from runtime.router.llm_router import LLMRouter
from runtime.state.state_manager import StateManager
from runtime.agent.controller import AgentController

class EzzioKernel:
    def __init__(self):
        self.memory = WorkingMemory()
        self.context_builder = ContextBuilder()
        self.router = LLMRouter()
        self.state_manager = StateManager()
        # Initialisation du contrôleur d'agent multi-tours
        self.agent_controller = AgentController(self.router, self.context_builder)

    def run_diagnostics(self) -> dict:
        persona_ok = (Path("registry/build/persona.production.md").exists() or Path("registry/persona.txt").exists())
        memory_ok = Path("runtime/memory/working_memory.json").exists()
        state_ok = Path("runtime/state/state.json").exists()
        ollama_ok = self.router.check_health()

        return {
            "persona": persona_ok,
            "memory": memory_ok,
            "state": state_ok,
            "ollama": ollama_ok
        }

    def chat(self, user_input: str, profile: str = "production") -> str:
        # 1. Enregistre le message utilisateur
        self.memory.add(role="user", content=user_input, source="terminal")

        # 2. Exécution de la boucle cognitive autonome via l'AgentController
        final_response = self.agent_controller.run_loop(user_input, self.memory, profile)

        # 3. Mémorisation et mise à jour de l'état
        self.memory.add(role="assistant", content=final_response, source="terminal")
        self.state_manager.update(last_action=f"agent_turn_{len(self.memory.messages)}")

        return final_response

if __name__ == "__main__":
    kernel = EzzioKernel()
    diag = kernel.run_diagnostics()

    print("=" * 60)
    print(f"=== 🧠 E-ZZIO RUNTIME KERNEL (Session ID: {kernel.memory.session_id}) ===")
    print("=" * 60)
    print(f"  • Persona compilée : " + ("✅ OK" if diag["persona"] else "❌ ABSENTE"))
    print(f"  • Mémoire de session : " + ("✅ OK" if diag["memory"] else "⚠ Initialisée"))
    print(f"  • État système (State) : " + ("✅ OK" if diag["state"] else "⚠ Initialisé"))
    print(f"  • Moteur Ollama local : " + ("✅ OK (Connecté)" if diag["ollama"] else "❌ INJOIGNABLE"))
    print(f"  • Agent Control Loop : ✅ Active (Multi-tours)")
    print(f"  • Modèle actif : {kernel.router.default_model}")
    print("-" * 60)
    print("Tape 'exit' ou 'quit' pour quitter.\n")

    while True:
        try:
            q = input("Toi > ")
            if q.lower() in ["exit", "quit"]:
                break
            if not q.strip():
                continue
            
            ans = kernel.chat(q)
            print(f"\nE-zzio > {ans}\n" + "-"*50)
        except KeyboardInterrupt:
            print("\nArrêt du kernel.")
            break