import asyncio
from typing import Dict, Any, Optional

# Correction de l'import depuis le package global model_router
from runtime.model_router import EzzioModelRouter, ModelRequest

class EzzioRealtimeRouter:
    """
    Pont isolé entre la couche Realtime (Pipecat/LiveKit) 
    et le noyau d'intelligence E-ZZIO (EzzioModelRouter).
    """
    def __init__(self, model_router: Optional[EzzioModelRouter] = None):
        self.model_router = model_router or EzzioModelRouter()

    async def process(self, text: str, task: str = "conversation", agent_id: str = "realtime_voice") -> Dict[str, Any]:
        """
        Traite un flux textuel issu de la voix, l'achemine vers le routeur de modèles
        et retourne la réponse structurée en préservant le ledger/modèle réel.
        """
        if not text or not text.strip():
            return {"content": "", "model_used": None, "provider_used": None, "ok": False}

        # Construction du contrat de requête standard E-ZZIO
        req = ModelRequest(
            prompt=text.strip(),
            task=task,
            complexity="low",
            latency="realtime",
            budget="local_first",
            system_prompt="Tu es E-zzio, un assistant vocal naturel, concis et direct."
        )

        # Exécution asynchrone non bloquante sur le routeur
        loop = asyncio.get_running_loop()
        try:
            response = await loop.run_in_executor(
                None, 
                lambda: self.model_router.generate(req, agent_id=agent_id)
            )

            # Extraction fidèle sans forcer de modèle par défaut artificiel
            if isinstance(response, dict):
                content = response.get("response") or response.get("content", "")
                model_used = response.get("model_used")
                provider_used = response.get("provider_used", "ollama")
            else:
                content = getattr(response, "content", "")
                model_used = getattr(response, "model_used", None)
                provider_used = getattr(response, "provider_used", "ollama")

            return {
                "ok": True,
                "content": content,
                "model_used": model_used,
                "provider_used": provider_used
            }
        except Exception as e:
            return {
                "ok": False,
                "content": f"Erreur de traitement vocal : {str(e)}",
                "model_used": None,
                "provider_used": None
            }
