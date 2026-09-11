"""
E-ZZIO Core — Cognitive Gateway (ECOL Canonique V10.1)
Agrégateur contextuel pur : Identité, Mémoire FTS5, Historique de session.
Délégation intégrale des contraintes au sous-système de routage (GATE A & GATE D).
"""
from __future__ import annotations
import os
import asyncio
import logging
from typing import Dict, Any, List, Optional
from core.agent.agent_provider import AgentProviderAdapter
from core.identity.canonical_identity import CanonicalIdentity
from core.memory.unified_gateway import UnifiedMemoryGateway

logger = logging.getLogger(__name__)


class CognitiveGateway:
    def __init__(self, db_path: str = "runtime/evidence/evidence.db"):
        self.db_path = db_path
        os.makedirs(os.path.dirname(db_path), exist_ok=True)
        self.memory_gateway = UnifiedMemoryGateway(db_path=db_path)
        self._initialized = False
        self._adapter: Optional[AgentProviderAdapter] = None
        self._background_tasks: set[asyncio.Task] = set()

        try:
            self.identity_provider = CanonicalIdentity()
        except Exception as e:
            logger.warning("[GATEWAY] Initialisation CanonicalIdentity impossible : %s", e)
            self.identity_provider = None

    async def init(self) -> None:
        """Initialisation asynchrone des composants mémoriels et de l'adaptateur."""
        if not self._initialized:
            await self.memory_gateway.init()
            if self._adapter is None:
                self._adapter = AgentProviderAdapter()
            self._initialized = True
            logger.info("[GATEWAY-CANONICAL] Mémoire et Adaptateur de routage initialisés.")

    def _persist_exchange(self, session_id: str, user_text: str, assistant_text: str) -> None:
        """Planifie l'écriture asynchrone dans la projection SQLite sans bloquer."""
        async def _save():
            try:
                await self.memory_gateway.record_message(session_id=session_id, role="user", content=user_text)
                await self.memory_gateway.record_message(session_id=session_id, role="assistant", content=assistant_text)
            except Exception as exc:
                logger.error("[ASYNC-SAVE-ERROR] %s", exc)

        task = asyncio.create_task(_save())
        self._background_tasks.add(task)
        task.add_done_callback(self._background_tasks.discard)

    async def ask_async(
        self,
        task: str,
        session_id: str = "default",
        priority: str = "normal",
        constraints: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Agrège le contexte et délègue l'arbitrage à la chaîne de routage.
        GATE A : Zéro sélection en dur du modèle ou du provider.
        GATE D : Priorité absolue de la session active sur les archives FTS5.
        """
        await self.init()

        # 1. Identité canonique (Inviolable)
        identity_prompt = "Tu es E-ZZIO, l'âme numérique souveraine conçue par ton créateur et Mentor BidiNani."
        if self.identity_provider:
            try:
                identity_prompt = self.identity_provider.build_system_prompt()
            except Exception as e:
                logger.error("[GATEWAY-IDENTITY-FAIL] %s", e)

        # 2. Rappel épisodique FTS5 (Archives antérieures informatives)
        episodic_context = ""
        try:
            search_res = await self.memory_gateway.search_memory(task, limit=2)
            relevant_past = search_res.get("chat_history", [])
            snippets = [
                f"- [Archive {m.get('timestamp', '')[:10]} / {m.get('role', 'unknown')}]: {m.get('content', '')}"
                for m in relevant_past
                if m.get("content", "").strip() != task.strip() and m.get("session_id") != session_id
            ]
            if snippets:
                episodic_context = (
                    "\n[ARCHIVES ÉPISODIQUES ANTÉRIEURES (Informatif — Ne prévaut pas sur la session en cours)]\n"
                    + "\n".join(snippets[:2])
                    + "\n"
                )
        except Exception as e:
            logger.debug("[GATEWAY-RECALL-SKIP] %s", e)

        full_system_prompt = identity_prompt + ("\n" + episodic_context if episodic_context else "")
        messages: List[Dict[str, str]] = [{"role": "system", "content": full_system_prompt}]

        # 3. Historique de la session active (Vérité courante Turn 1..N-1)
        try:
            history = await self.memory_gateway.get_session_history(session_id=session_id, limit=6)
            for h in history:
                r = h.get("role", "user")
                c = h.get("content", "")
                if r in ["user", "assistant"] and c:
                    messages.append({"role": r, "content": c})
        except Exception as e:
            logger.debug("[GATEWAY-HISTORY-SKIP] %s", e)

        # 4. Message utilisateur actuel (Turn N)
        messages.append({"role": "user", "content": task})

        # 5. Délégation d'exécution au routeur avec transmission des contraintes
        try:
            # L'adaptateur de routage est l'unique autorité de résolution
            force_cloud_flag = bool(constraints.get("force_cloud", False)) if constraints else False
            response_text = self._adapter.chat_completion(messages=messages, force_cloud=force_cloud_flag)
            self._persist_exchange(session_id, task, response_text)

            return {
                "status": "ACCEPTED",
                "task": task,
                "session_id": session_id,
                "injected_context_depth": len(messages),
                "result": response_text,
            }
        except Exception as e:
            logger.error("[GATEWAY-CRITICAL] Échec d'inférence : %s", e)
            return {
                "status": "FAILED",
                "task": task,
                "session_id": session_id,
                "error": str(e),
            }

    def ask(
        self,
        task: str,
        session_id: str = "default",
        priority: str = "normal",
        constraints: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Passerelle synchrone."""
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                return asyncio.run_coroutine_threadsafe(
                    self.ask_async(task, session_id, priority, constraints), loop
                ).result()
            return loop.run_until_complete(
                self.ask_async(task, session_id, priority, constraints)
            )
        except RuntimeError:
            return asyncio.run(
                self.ask_async(task, session_id, priority, constraints)
            )
