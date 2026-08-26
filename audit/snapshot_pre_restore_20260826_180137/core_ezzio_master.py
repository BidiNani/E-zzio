"""E-ZZIO Master Orchestrator — Cloud-Only Fail-Closed v4.0.0."""
from __future__ import annotations
from typing import Any, Dict
from core.memory_vault import check_memory_intent
from core.dispatcher import ezzio_dispatcher
from core.memory import ezzio_memory
from core import safe_actions

class EzzioMasterOrchestrator:
    def __init__(self) -> None:
        self.dispatcher = ezzio_dispatcher
        self.memory = ezzio_memory
        self.ledger = safe_actions.ledger

    async def execute_intent(self, user_prompt: str, speed: str = "auto", force_cloud: bool = False, session_id: str = "", system_prompt: str = "") -> Dict[str, Any]:
        vault_res = check_memory_intent(user_prompt)
        if vault_res:
            return {
                "organ": "memory_vault",
                "source": "Deterministic SQLite",
                "response": {"response": vault_res, "text": vault_res, "model": "sqlite_vault", "elapsed_ms": 1},
                "ok": True,
                "used_fallback": False,
            }

        organ_key, organ_info, score, hits = self.dispatcher.select_organ(user_prompt)
        selected_model = self.dispatcher.select_model_for_speed(organ_info, speed)

        cloud_result = await self.dispatcher.route_detailed_async(
            text=user_prompt,
            speed=speed,
            session_id=session_id,
            system_prompt=system_prompt,
            force_cloud=True,
        )

        if not isinstance(cloud_result, dict):
            fail_msg = "[FAIL-CLOSED] Contrat dispatcher invalide : réponse non-dictionnaire."
            return {
                "organ": organ_key,
                "source": "Cloud-Only / Contract Failure",
                "response": fail_msg,
                "model": "none",
                "selected_model": selected_model,
                "route_score": score,
                "route_hits": hits,
                "ok": False,
                "used_fallback": False,
            }

        if cloud_result.get("ok") is False:
            return {
                "organ": organ_key,
                "source": "Gemini Cloud / FAIL-CLOSED",
                "response": cloud_result,
                "model": cloud_result.get("model", "none"),
                "selected_model": selected_model,
                "route_score": score,
                "route_hits": hits,
                "ok": False,
                "used_fallback": False,
            }

        response_text = (
            cloud_result.get("response")
            or cloud_result.get("answer")
            or cloud_result.get("message")
            or cloud_result.get("content")
            or str(cloud_result)
        )

        return {
            "organ": organ_key,
            "source": "Gemini Cloud — Cloud-Only",
            "response": response_text,
            "model": cloud_result.get("model", selected_model),
            "selected_model": selected_model,
            "route_score": score,
            "route_hits": hits,
            "ok": True,
            "used_fallback": False,
            "cloud_result": cloud_result,
        }

ezzio_master = EzzioMasterOrchestrator()
