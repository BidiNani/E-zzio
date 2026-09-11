"""E-ZZIO Master Orchestrator — Mono-Autorité Identitaire & Conversationnel.

Version épurée : GeminiProvider direct, plus de fédération/missions/workers.
"""
from __future__ import annotations
import re
import uuid
import time
import asyncio
import logging
from datetime import datetime, timezone
from typing import Any, Dict, Optional, List

from core.providers.gemini_provider import GeminiProvider
from core.providers.base_provider import ProviderResponse
from core.memory.instance import memory_gateway

logger = logging.getLogger("EzzioMaster")

_command_ledger = None


def _audit_command(action: str, payload: Dict[str, Any],
                   status: str = "SUCCESS") -> None:
    """Chaîne d'audit des commandes : ledger scellé, jamais bloquant."""
    global _command_ledger
    try:
        if _command_ledger is None:
            from core.security.audit_ledger import AuditLedger
            _command_ledger = AuditLedger()
        import sys as _sys
        payload = dict(payload or {})
        payload.setdefault(
            "env", "test" if "pytest" in _sys.modules else "prod")
        _command_ledger.record_event(actor="ezzio-master", action=action,
                                     payload=payload, status=status)
    except Exception as exc:
        logger.warning("[EzzioMaster] Audit commande non enregistré : %s", exc)


class EzzioMaster:
    """Orchestrateur central E-ZZIO : conversation via GeminiProvider direct."""

    def __init__(self, provider: Optional[GeminiProvider] = None, **kwargs: Any) -> None:
        self.provider = provider or GeminiProvider()
        self.memory = memory_gateway
        self._memory_initialized = False

    async def _record_assistant_memory(self, res_dict: Dict[str, Any],
                                       session_id: str, channel: str) -> Dict[str, Any]:
        if session_id and res_dict.get("response"):
            try:
                if not self._memory_initialized:
                    await self.memory.init()
                    self._memory_initialized = True
                _meta = {
                    "channel": channel,
                    "model": res_dict.get("model"),
                    "provider": res_dict.get("provider"),
                }
                if res_dict.get("truth_gate"):
                    _meta["truth_gate"] = res_dict.get("truth_gate")
                await self.memory.record_message(
                    session_id=session_id,
                    role="assistant",
                    content=res_dict["response"],
                    metadata=_meta
                )
            except Exception as exc:
                logger.warning("[EzzioMaster] Memory record assistant failed: %s", exc)
        return res_dict

    async def _build_chat_system_prompt(self, session_id: str = "") -> Optional[str]:
        """Identité canonique + derniers échanges."""
        try:
            from core.identity.canonical_identity import CanonicalIdentity
            persona = CanonicalIdentity().build_system_prompt()
        except Exception:
            persona = ("Tu es E-ZZIO, orchestrateur souverain : direct, concis, loyal, "
                       "jamais un autre modèle. Tu réponds en français.")
        ctx_lines: List[str] = []
        if session_id:
            try:
                if not self._memory_initialized:
                    await self.memory.init()
                    self._memory_initialized = True
                hist = await self.memory.get_session_history(session_id, limit=6)
                for h in (hist or [])[-6:]:
                    role = "Utilisateur" if h.get("role") == "user" else "Assistant"
                    ctx_lines.append(f"{role} : {str(h.get('content', ''))[:400]}")
            except Exception:
                pass
        parts = [persona.strip(), "- Réponds en français, direct et concis.",
                 "- Tu es E-ZZIO, jamais Hermes ni un autre modèle."]
        if ctx_lines:
            parts.append("Contexte récent :\n" + "\n".join(ctx_lines))
        return "\n\n".join(parts)

    async def execute_intent(
        self,
        user_prompt: str,
        speed: str = "auto",
        force_cloud: bool = False,
        session_id: str = "",
        system_prompt: str = "",
        mission_profile: str = "STANDARD",
        model_target: Optional[str] = "auto",
        channel: str = "web",
        user_id: str = "operator",
        **kwargs: Any
    ) -> Dict[str, Any]:
        """Exécute la requête utilisateur via GeminiProvider direct."""
        start_time = time.perf_counter()

        if session_id:
            try:
                if not self._memory_initialized:
                    await self.memory.init()
                    self._memory_initialized = True
                await self.memory.record_message(
                    session_id=session_id,
                    role="user",
                    content=user_prompt,
                    metadata={"channel": channel, "user_id": user_id}
                )
            except Exception as exc:
                logger.warning("[EzzioMaster] Memory record user prompt failed: %s", exc)

        try:
            chat_system = system_prompt or await self._build_chat_system_prompt(session_id)
            resp: ProviderResponse = await self.provider.generate(
                prompt=user_prompt or "",
                system_prompt=chat_system if chat_system else None,
                model="gemini-3.7-flash",
                temperature=0.2,
                max_tokens=512,
            )
            elapsed_ms = int((time.perf_counter() - start_time) * 1000)

            reply = resp.content or ""
            model_name = resp.model or "gemini-3.7-flash"
            provider_name = resp.provider or "gemini"

            if not reply.strip():
                _audit_command("PROVIDER_EMPTY", {
                    "provider": provider_name, "model": model_name,
                    "outcome": "REFUSED"}, "BLOCKED")
                raise RuntimeError(
                    "[FAIL-CLOSED] Provider sans réponse exécutable : exécution refusée.")

            res_conv = {
                "response": reply,
                "answer": reply,
                "content": reply,
                "message": reply,
                "source": f"{provider_name} ({model_name})",
                "authority": "CanonicalIdentity",
                "model": model_name,
                "provider": provider_name,
                "mission": mission_profile or "STANDARD",
                "channel": channel,
                "elapsed_ms": elapsed_ms,
                "ok": True,
                "used_fallback": False,
            }
            _audit_command("CONV_MODEL", {
                "model": model_name, "provider": provider_name,
                "outcome": "RESPONDED",
                "session_id": session_id or ""})
            return await self._record_assistant_memory(res_conv, session_id, channel)

        except Exception as exc:
            elapsed_ms = int((time.perf_counter() - start_time) * 1000)
            logger.error("[EzzioMaster] Exception during execution: %s", exc)

            _audit_command("PROVIDER_EXCEPTION", {
                "error": str(exc)[:300],
                "outcome": "REFUSED"}, "BLOCKED")
            fail_msg = f"[FAIL-CLOSED] Provider E-ZZIO indisponible : {exc}"
            res_fail = {
                "response": fail_msg,
                "answer": fail_msg,
                "content": fail_msg,
                "message": fail_msg,
                "source": "Provider Fail-Closed",
                "authority": "CanonicalIdentity",
                "model": "none",
                "provider": "none",
                "mission": mission_profile or "STANDARD",
                "channel": channel,
                "elapsed_ms": elapsed_ms,
                "ok": False,
                "error": str(exc),
                "used_fallback": False,
            }
            return await self._record_assistant_memory(res_fail, session_id, channel)


ezzio_master = EzzioMaster()