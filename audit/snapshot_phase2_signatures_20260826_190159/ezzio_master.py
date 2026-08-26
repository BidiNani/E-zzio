"""E-ZZIO Master Orchestrator — Architecture Cloud-First Pure (Gemini 3.5 Flash-Lite)."""
from __future__ import annotations
from typing import Any, Dict
from core.memory_vault import check_memory_intent
from core.cloud_brain_broker import cloud_chat


class EzzioMasterOrchestrator:
    async def execute_intent(
        self,
        user_prompt: str,
        speed: str = "fast",
        force_cloud: bool = True,
        session_id: str = "",
        system_prompt: str = ""
    ) -> Dict[str, Any]:
        # 1. Mémoire SQLite Déterministe (0 ms si présent)
        vault_res = check_memory_intent(user_prompt)
        if vault_res:
            return {
                "organ": "memory_vault",
                "source": "Deterministic SQLite",
                "response": vault_res,
                "model": "sqlite_vault",
                "ok": True,
                "used_fallback": False,
            }

        # 2. Inférence directe Gemini 3.5 Flash-Lite
        try:
            cloud_res = cloud_chat(
                text=user_prompt,
                session_id=session_id,
                system_prompt=system_prompt,
                speed=speed
            )

            response_text = (
                cloud_res.get("response")
                or cloud_res.get("answer")
                or cloud_res.get("content")
                or cloud_res.get("message")
                or str(cloud_res)
            )

            return {
                "organ": "cloud_brain",
                "source": "Gemini 3.5 Flash-Lite",
                "response": response_text.strip(),
                "model": cloud_res.get("model", "gemini-3.5-flash-lite"),
                "ok": cloud_res.get("ok", True),
                "used_fallback": False,
            }

        except Exception as exc:
            fail_msg = f"[FAIL-CLOSED] Liaison Gemini 3.5 Flash-Lite indisponible : {exc}"
            return {
                "organ": "cloud_brain",
                "source": "Gemini Cloud Fail-Closed",
                "response": fail_msg,
                "model": "none",
                "ok": False,
                "used_fallback": False,
            }


ezzio_master = EzzioMasterOrchestrator()
