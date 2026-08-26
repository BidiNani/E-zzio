"""Dispatcher centralisé - Intégration complète avec barrière absolue Cloud-Only."""

from typing import Any, Dict, Tuple
from core.cloud_brain_broker import cloud_chat

class EzzioDispatcher:
    """Gestionnaire de routage principal d'E-zzio avec verrou Cloud-Only strict."""
    
    def __init__(self):
        pass

    def select_organ(self, prompt: str) -> Tuple[str, Dict[str, Any], int, list]:
        """Sélection d'organe compatible avec ezzio_master.py."""
        organ_info = {"label": "Souverain (Cloud-Only)", "organ": "presence"}
        return "presence", organ_info, 100, ["gemini_cloud_only"]

    def select_model_for_speed(self, organ_info: dict, speed: str = "fast") -> str:
        """Sélection du modèle cloud unique pour le canal sécurisé."""
        return "gemini-3.5-flash-lite"

    def dispatch(self, text: str, session_id: str = "", system_prompt: str = "", speed: str = "fast", force_cloud: bool = False) -> Dict[str, Any]:
        is_discord = session_id and str(session_id).startswith("disc_user_")
        
        # BARRIÈRE ABSOLUE : Trafic Discord / Cloud forcé route vers Gemini exclusivement
        if is_discord or force_cloud:
            try:
                return cloud_chat(text, session_id=session_id, system_prompt=system_prompt, speed=speed)
            except Exception as exc:
                fail_msg = f"[FAIL-CLOSED] Liaison Gemini interrompue : {str(exc)}. Aucun repli local autorisé."
                return {
                    "response": fail_msg,
                    "answer": fail_msg,
                    "message": fail_msg,
                    "content": fail_msg,
                    "model": "none",
                    "primary_model": "none",
                    "deep_model": "none",
                    "attempted_models": [],
                    "fallback_models": [],
                    "used_fallback": False,
                    "ok": False
                }

        return {
            "response": "[ERREUR] Contexte non-Discord rejeté par la politique Cloud-Only.",
            "answer": "[ERREUR]",
            "used_fallback": False
        }

# Instance singleton requise par ezzio_master.py
ezzio_dispatcher = EzzioDispatcher()

def dispatch(text: str, session_id: str = "", system_prompt: str = "", speed: str = "fast", force_cloud: bool = False) -> Dict[str, Any]:
    return ezzio_dispatcher.dispatch(text, session_id=session_id, system_prompt=system_prompt, speed=speed, force_cloud=force_cloud)
