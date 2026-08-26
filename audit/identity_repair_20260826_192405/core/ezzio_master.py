"""E-ZZIO Master Orchestrator — Mono-Autorité Identitaire et Inférence Directe."""
from __future__ import annotations
import time
from typing import Any, Dict
from core.cloud_brain_broker import cloud_chat


class EzzioMaster:
    """Orchestrateur central E-ZZIO."""

    async def execute_intent(
        self,
        user_prompt: str,
        speed: str = "fast",
        force_cloud: bool = True,
        session_id: str = "",
        **kwargs
    ) -> Dict[str, Any]:
        """
        Exécute la requête utilisateur.
        L'identité est injectée exclusivement par CanonicalIdentity en aval dans cloud_brain_broker.
        """
        start_time = time.perf_counter()
        
        try:
            cloud_res = cloud_chat(
                text=user_prompt,
                session_id=session_id,
                speed=speed,
                provider="gemini"
            )
            elapsed_ms = int((time.perf_counter() - start_time) * 1000)

            reply = cloud_res.get("response") or cloud_res.get("answer") or cloud_res.get("content") or ""
            model_name = cloud_res.get("model", "gemini-2.5-flash")
            
            return {
                "response": reply,
                "answer": reply,
                "content": reply,
                "message": reply,
                "source": f"Gemini Cloud ({model_name})",
                "authority": "CanonicalIdentity",
                "model": model_name,
                "elapsed_ms": elapsed_ms,
                "ok": True,
                "used_fallback": False
            }
        except Exception as exc:
            fail_msg = f"[FAIL-CLOSED] Liaison Cloud Brain indisponible : {exc}"
            return {
                "response": fail_msg,
                "answer": fail_msg,
                "content": fail_msg,
                "message": fail_msg,
                "source": "Gemini Cloud Fail-Closed",
                "authority": "CanonicalIdentity",
                "model": "none",
                "elapsed_ms": int((time.perf_counter() - start_time) * 1000),
                "ok": False,
                "error": str(exc),
                "used_fallback": False
            }


ezzio_master = EzzioMaster()
