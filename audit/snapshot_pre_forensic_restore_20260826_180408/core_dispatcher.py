"""E-ZZIO Dispatcher — Contrat Cloud-Only Fail-Closed v4.0.0."""
from __future__ import annotations
from typing import Any, Dict, Tuple
from core.cloud_brain_broker import cloud_chat

TARGET_MODEL = "gemini-3.5-flash-lite"

def _fail_closed(message: str) -> Dict[str, Any]:
    return {
        "response": message,
        "answer": message,
        "message": message,
        "content": message,
        "model": "none",
        "primary_model": "none",
        "deep_model": "none",
        "attempted_models": [],
        "fallback_models": [],
        "used_fallback": False,
        "ok": False,
        "route_score": 0,
        "route_hits": ["cloud_only_fail_closed"],
        "gpu_policy": "disabled_for_ezzio",
        "num_gpu": 0,
    }

class EzzioDispatcher:
    def __init__(self) -> None:
        self.target_model = TARGET_MODEL

    def select_organ(self, prompt: str) -> Tuple[str, Dict[str, Any], int, list]:
        organ_info: Dict[str, Any] = {
            "label": "Souverain (Cloud-Only)",
            "organ": "presence",
            "priority": 10,
            "provider": "gemini",
            "model": self.target_model,
            "execution_mode": "cloud_only",
            "fallback_allowed": False,
        }
        return ("presence", organ_info, 100, ["gemini_cloud_only", "fail_closed"])

    def select_model_for_speed(self, organ_info: dict, speed: str = "fast") -> str:
        return self.target_model

    async def route_detailed_async(self, text: str, speed: str = "fast", session_id: str = "", system_prompt: str = "", force_cloud: bool = True) -> Dict[str, Any]:
        try:
            result = cloud_chat(text=text, session_id=session_id, system_prompt=system_prompt, speed=speed)
            if not isinstance(result, dict):
                return _fail_closed("[FAIL-CLOSED] Broker Cloud a retourné un résultat non conforme.")
            return result
        except Exception as exc:
            return _fail_closed(f"[FAIL-CLOSED] Exception du broker Gemini : {exc}")

    async def dispatch_async(self, text: str, session_id: str = "", system_prompt: str = "", speed: str = "fast", force_cloud: bool = True) -> Dict[str, Any]:
        return await self.route_detailed_async(text=text, speed=speed, session_id=session_id, system_prompt=system_prompt, force_cloud=True)

    def dispatch(self, text: str, session_id: str = "", system_prompt: str = "", speed: str = "fast", force_cloud: bool = True) -> Dict[str, Any]:
        try:
            result = cloud_chat(text=text, session_id=session_id, system_prompt=system_prompt, speed=speed)
            if not isinstance(result, dict):
                return _fail_closed("[FAIL-CLOSED] Réponse broker non conforme.")
            return result
        except Exception as exc:
            return _fail_closed(f"[FAIL-CLOSED] Liaison Gemini interrompue : {exc}")

ezzio_dispatcher = EzzioDispatcher()

def dispatch(text: str, session_id: str = "", system_prompt: str = "", speed: str = "fast", force_cloud: bool = False) -> Dict[str, Any]:
    return ezzio_dispatcher.dispatch(text=text, session_id=session_id, system_prompt=system_prompt, speed=speed, force_cloud=force_cloud)

