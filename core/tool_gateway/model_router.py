"""
E-ZZIO V7.41 — Multi Model Intelligence Router
Orchestre et dirige les requêtes cognitives vers le LLM approprié (Gemini Pro, Ollama)
via la Tool Gateway sécurisée.
"""

import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from core.tool_gateway.gateway_controller import tool_gateway


class MultiModelRouter:
    def __init__(self):
        self.models = {
            "gemini_pro": {"tool": "gemini_inference", "cost": "api_quota"},
            "ollama_local": {"tool": "ollama_inference", "cost": "local_compute"},
        }

    def _evaluate_routing(self, task_type: str, complexity_score: int) -> str:
        """Détermine le modèle optimal selon la tâche et la complexité (1 à 10)."""
        heavy_tasks = ["architecture", "deep_analysis", "coding", "creative_writing"]

        if complexity_score > 6 or task_type in heavy_tasks:
            return "gemini_pro"
        return "ollama_local"

    def execute_prompt(self, prompt: str, task_type: str = "general", complexity: int = 5) -> dict:
        selected_model = self._evaluate_routing(task_type, complexity)
        tool_name = self.models[selected_model]["tool"]

        # Le routage passe obligatoirement par la Tool Gateway V7.39
        gateway_res = tool_gateway.request_action(
            tool_name=tool_name, payload={"prompt": prompt, "model_target": selected_model}, intent=f"LLM Inference via {selected_model}"
        )

        # En production, l'appel API réel serait effectué ici si le statut est APPROVED
        api_executed = gateway_res.get("status") in ["APPROVED_AUTO", "APPROVED_WITH_AUDIT"]

        return {
            "routed_to": selected_model,
            "gateway_status": gateway_res.get("status"),
            "action_id": gateway_res.get("action_id"),
            "api_executed": api_executed,
            "simulated_response": f"[MOCK] Réponse de {selected_model} générée." if api_executed else None,
        }


model_router = MultiModelRouter()
