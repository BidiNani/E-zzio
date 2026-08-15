"""
E-ZZIO Core — Legacy LLM Adapter (ECOL)
Intercepte les anciens appels directs (Ollama, API) et les redirige vers 
la Cognitive Gateway pour appliquer l'économie cognitive et le filtrage d'identité.
"""
import logging
from typing import Dict, Any, List

# On importe la Gateway unique
try:
    from core.cognition.cognitive_gateway import CognitiveGateway
except ImportError:
    # Fallback pour le déploiement/test isolé
    CognitiveGateway = None

logger = logging.getLogger(__name__)

class LegacyLLMAdapter:
    def __init__(self):
        logger.info("Initialisation de l'adaptateur Legacy LLM -> ECOL Gateway...")
        self.gateway = CognitiveGateway() if CognitiveGateway else None

    def intercept_ollama_chat(self, model: str, messages: List[Dict[str, str]], **kwargs) -> Dict[str, Any]:
        """
        Intercepte un appel de type ollama.chat().
        Le vieux module pense parler à Ollama, mais il parle à l'ECOL.
        """
        logger.warning("[LEGACY INTERCEPT] Appel direct Ollama détecté. Redirection vers ECOL.")
        
        # 1. Extraction de l'intention à partir des messages bruts
        task_description = messages[-1]['content'] if messages else "Tâche indéfinie"
        
        # 2. Encapsulation pour la Gateway
        context_payload = {
            "legacy_model_requested": model,
            "legacy_messages": messages[:-1],  # Le contexte historique brut
            "legacy_kwargs": kwargs,
            "source": "ollama_adapter"
        }
        
        # 3. Passage par la porte unique ECOL
        if self.gateway:
            ecol_response = self.gateway.ask(
                task=task_description,
                priority="normal",
                context_payload=context_payload
            )
            result_content = ecol_response.get("result", "Erreur ECOL interne.")
        else:
            result_content = "Mode bypass : Gateway non initialisée."

        # 4. Mocking de la réponse pour ne pas faire crasher le vieux module
        return {
            "model": "ecol-routed-model",
            "created_at": "ECOL_INTERCEPTED",
            "message": {
                "role": "assistant",
                "content": result_content
            },
            "done": True,
            "ecol_budget_applied": True
        }

    def intercept_api_call(self, endpoint: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        """
        Intercepte les appels API REST classiques (ex: requêtes OpenAI/Claude).
        """
        logger.warning(f"[LEGACY INTERCEPT] Appel API externe ({endpoint}) intercepté.")
        
        # Traduction similaire pour les appels API...
        return {
            "choices": [{
                "message": {
                    "role": "assistant",
                    "content": "Requête API externe bloquée et traitée par ECOL."
                }
            }],
            "ecol_intercepted": True
        }
