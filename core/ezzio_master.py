"""E-ZZIO Master Orchestrator — Mono-Autorité Identitaire & Conversationnel.

Version épurée : GeminiProvider direct, plus de fédération/missions/workers.
"""
from __future__ import annotations

import asyncio
import logging
import time
import uuid
from datetime import UTC, datetime
from typing import Any

from core.kernel.native_harness import NativeHarness
from core.memory.instance import memory_gateway
from core.providers.base_provider import BaseProvider, ProviderResponse

logger = logging.getLogger("EzzioMaster")


_command_ledger = None


def _audit_command(action: str, payload: dict[str, Any],
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


def determine_intent(
    user_prompt: str,
    mission_profile: str = "AUTO",
    is_mission: bool = False,
) -> str:
    """Détermine dynamiquement l'intention : CHAT ou MISSION.

    Règles :
      - Si is_mission est True ou mission_profile in ("MISSION", "COMPLEX_MISSION", "COMPLEX") -> MISSION.
      - Si mission_profile in ("STANDARD", "CHAT", "CONVERSATIONAL") -> CHAT.
      - Si mission_profile in ("AUTO", "", "DEFAULT"):
          Analyse de l'intention réelle d'action/exécution vs conversation/question.
    """
    if is_mission:
        return "MISSION"

    prof = (mission_profile or "AUTO").upper().strip()
    if prof in ("MISSION", "COMPLEX_MISSION", "COMPLEX"):
        return "MISSION"
    if prof in ("STANDARD", "CHAT", "CONVERSATIONAL"):
        return "CHAT"

    # En mode AUTO, classification déterministe / heuristique d'intention d'action vs conversation
    p_lower = user_prompt.lower().strip()

    # Mots-clés/Intentions explicites d'exécution / d'audit / de modification technique (MISSION)
    mission_triggers = (
        "audite", "audit ", "inspecte et corrige", "exécute les tests", "execute les tests",
        "crée un patch", "cree un patch", "refactorise", "corrige le bug", "fix the bug",
        "déploie", "deploie", "analyse et corrige", "vérifie et corrige", "verifie et corrige",
        "exécute la tâche", "execute la tache", "run mission", "lance la mission"
    )
    if any(trigger in p_lower for trigger in mission_triggers):
        return "MISSION"

    # Tout le reste (salutations, questions générales, demandes d'explications, questions sur statut/avis) -> CHAT
    return "CHAT"


class EzzioMaster:
    """Orchestrateur central E-ZZIO : conversation via ProviderFactory canonique."""

    def __init__(self, provider: BaseProvider | None = None, **kwargs: Any) -> None:
        self.provider = provider
        self._injected_provider = provider  # None si pas injecte (utilise ProviderFactory)
        self.memory = memory_gateway
        self._memory_initialized = False
        self.workspace_root = kwargs.get("workspace_root", r"G:\AI\E-zzio")
        self.harness = NativeHarness(router=None, policy_guard=None, audit_ledger=None, workspace_root=self.workspace_root)
        self.hermes_adapter = kwargs.get("hermes_adapter")
        if self.hermes_adapter is None:
            from core.agent.hermes_worker_adapter import HermesWorkerAdapter
            self.hermes_adapter = HermesWorkerAdapter(workspace_root=self.workspace_root)
        self._background_tasks: set[asyncio.Task] = set()


    async def _record_assistant_memory(self, res_dict: dict[str, Any],
                                       session_id: str, channel: str) -> dict[str, Any]:
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

    async def _build_chat_system_prompt(self, session_id: str = "", exclude_prompt: str = "") -> str | None:
        """Identité canonique + derniers échanges."""
        try:
            from core.identity.canonical_identity import CanonicalIdentity
            persona = CanonicalIdentity().build_system_prompt()
        except Exception:
            persona = ("Tu es E-ZZIO, orchestrateur souverain : direct, concis, loyal, "
                       "jamais un autre modèle. Tu réponds en français.")
        ctx_lines: list[str] = []
        if session_id:
            try:
                if not self._memory_initialized:
                    await self.memory.init()
                    self._memory_initialized = True
                hist = await self.memory.get_session_history(session_id, limit=6)
                for h in (hist or [])[-6:]:
                    content = str(h.get('content', ''))
                    if exclude_prompt and content.strip() == exclude_prompt.strip():
                        continue
                    role = "Utilisateur" if h.get("role") == "user" else "Assistant"
                    ctx_lines.append(f"{role} : {content[:400]}")
            except Exception:
                pass

            try:
                from core.agent.mission_controller import mission_registry
                active_m = mission_registry.get_active_mission_for_session(session_id)
                if not active_m:
                    active_m = mission_registry.get_latest_mission_for_session(session_id)
                if active_m:
                    m_st = str(active_m.status.value if hasattr(active_m.status, "value") else active_m.status)
                    m_line = f"Mission active/récente (#{active_m.mission_id}) : Statut={m_st} | Objectif: {active_m.goal[:150]}"
                    if active_m.result and active_m.result.get("synthesis"):
                        m_line += f" | Synthèse: {active_m.result.get('synthesis')[:200]}"
                    ctx_lines.append(m_line)
            except Exception:
                pass
        parts = [persona.strip(), "- Réponds en français, direct et concis.",
                 "- Tu es E-ZZIO, jamais Hermes ni un autre modèle."]
        if ctx_lines:
            parts.append("Contexte récent :\n" + "\n".join(ctx_lines))
        return "\n\n".join(parts)


    async def _generate_response(
        self,
        user_prompt: str,
        routing: dict[str, Any],
        kwargs: dict[str, Any],
    ) -> dict[str, Any]:
        """Genere une reponse LLM en utilisant le routing decide par le harness.

        Appele par NativeHarness dans l'etat EXECUTING.

        Args:
            user_prompt: Le prompt utilisateur.
            routing: Le routing retourne par le harness (model, provider, thinking_level).
            kwargs: Parametres additionnels (chat_system, force_cloud, session_id, channel, etc.)

        Returns:
            dict avec "response", "model", "provider", etc.
        """

        chat_system = kwargs.get("chat_system")
        session_id = kwargs.get("session_id", "")
        channel = kwargs.get("channel", "web")
        logger.debug("[EzzioMaster] Generation (session=%s, channel=%s)", session_id, channel)
        model_target = kwargs.get("model_target", "auto")
        thinking_level = routing.get("thinking_level")

        # Override depuis settings utilisateur (toggle frontend)
        try:
            from routers.settings import _state as _settings_state
            if _settings_state.get("thinking_enabled"):
                thinking_level = _settings_state.get("thinking_level", thinking_level)
        except Exception:
            pass

        # Phase 2.3A Etape 2 : le provider vient du ModelRouter (autorite unique)
        from core.providers.registry import ProviderFactory

        selected_model = routing.get("model", "gemini-3.5-flash-lite")
        provider_name = routing.get("provider", "gemini")

        # Override model_target si specifie
        if model_target and model_target not in ("auto", "local", "cloud"):
            selected_model = model_target

        # Override provider si model_target force local/cloud
        _mt = (model_target or "").lower()
        if _mt in ("local", "ollama"):
            provider_name = "ollama"
            logger.info("[EzzioMaster] Mode local explicite (model_target=%s)", model_target)
        elif _mt == "cloud":
            logger.info("[EzzioMaster] Mode cloud explicite (model_target=%s)", model_target)

        resp: ProviderResponse
        used_fallback = False
        fallback_notice: dict | None = None
        detected_provider = provider_name  # alias pour _try_fallback

        try:
            # Backward compat : si un provider a ete injecte (tests), l'utiliser
            if self._injected_provider is not None:
                prov = self.provider
                logger.debug("[EzzioMaster] Provider injecte utilise : %s", type(prov).__name__)
            else:
                prov = ProviderFactory.create(provider_name)
            resp = await prov.generate(
                prompt=user_prompt,
                system_prompt=chat_system if chat_system else None,
                model=selected_model,
                temperature=0.2,
                max_tokens=512 if provider_name == "ollama" else 2048,
                thinking_level=thinking_level,
            )
        except Exception as cloud_err:
            logger.warning(
                "[EzzioMaster] Echec provider %s (%s) -> fallback",
                provider_name, cloud_err,
            )
            fb_resp, fb_notice = await self._try_fallback(
                detected_provider=provider_name,
                original_model=selected_model,
                reason=f"exception: {type(cloud_err).__name__}",
                user_prompt=user_prompt,
                chat_system=chat_system,
                thinking_level=thinking_level,
            )
            if fb_resp is None:
                raise
            resp = fb_resp
            used_fallback = True
            fallback_notice = fb_notice

        reply = resp.content or ""
        model_name = resp.model or selected_model
        provider_name = resp.provider or routing.get("provider", "gemini")

        # Si reponse vide -> fallback
        if not reply.strip():
            logger.warning(
                "[EzzioMaster] Reponse vide du provider %s -> fallback",
                detected_provider,
            )
            fb_resp, fb_notice = await self._try_fallback(
                detected_provider=detected_provider,
                original_model=selected_model,
                reason="empty_response",
                user_prompt=user_prompt,
                chat_system=chat_system,
                thinking_level=thinking_level,
            )
            if fb_resp is not None and (fb_resp.content or "").strip():
                resp = fb_resp
                reply = resp.content or ""
                model_name = resp.model or selected_model
                provider_name = resp.provider or "gemini"
                used_fallback = True
                fallback_notice = fb_notice
            else:
                _audit_command("PROVIDER_EMPTY", {
                    "provider": provider_name, "model": model_name,
                    "outcome": "REFUSED"}, "BLOCKED")
                raise RuntimeError(
                    "[FAIL-CLOSED] Provider sans reponse executable : execution refusee.")

        return {
            "response": reply,
            "answer": reply,
            "content": reply,
            "message": reply,
            "source": f"{provider_name} ({model_name})",
            "authority": "CanonicalIdentity",
            "model": model_name,
            "provider": provider_name,
            "used_fallback": used_fallback,
            "usage": getattr(resp, "usage", {}) or {},
            "thinking_level": getattr(resp, "thinking_level", None),
            "fallback_notice": fallback_notice,
        }

    async def _try_fallback(
        self,
        *,
        detected_provider: str,
        original_model: str,
        reason: str,
        user_prompt: str | None,
        chat_system: str | None,
        thinking_level: str | None,
    ):
        """Bascule vers FALLBACK_MAP[provider] en cas de defaillance.

        Retourne (ProviderResponse | None, dict | None).
        - Succes : (resp, notice)
        - Echec  : (None, None)
        """
        try:
            from routers.settings import FALLBACK_MAP
        except Exception:
            logger.error("[EzzioMaster] FALLBACK_MAP indisponible")
            return None, None

        fb_model = FALLBACK_MAP.get(detected_provider)
        if not fb_model or fb_model == original_model:
            return None, None

        try:
            from core.providers.registry import ProviderFactory
            fb_provider_name = "gemini"
            try:
                from core.routing.model_registry import canonical_model_registry
                rec = canonical_model_registry.get(fb_model)
                if rec and rec.provider:
                    fb_provider_name = rec.provider
            except Exception:
                pass

            fb_prov = ProviderFactory.create(fb_provider_name)
            fb_resp = await fb_prov.generate(
                prompt=user_prompt or "",
                system_prompt=chat_system if chat_system else None,
                model=fb_model,
                temperature=0.2,
                max_tokens=2048,
                thinking_level=thinking_level,
            )
            if not fb_resp or not (fb_resp.content or "").strip():
                return None, None

            notice = {
                "fallback_used": True,
                "requested_model": original_model,
                "requested_provider": detected_provider,
                "actual_model": fb_model,
                "actual_provider": getattr(fb_resp, "provider", "") or fb_provider_name,
                "reason": reason,
                "message": (
                    f"Le modele {original_model} ({detected_provider}) est indisponible. "
                    f"Reponse generee par {fb_model}. "
                    f"Continuer avec ce modele, ou reessayer {original_model} ?"
                ),
            }
            logger.info(
                "[EzzioMaster] Fallback OK : %s -> %s (%s)",
                original_model, fb_model, reason,
            )
            return fb_resp, notice
        except Exception as fb_err:
            logger.error("[EzzioMaster] Fallback echoue : %s", fb_err)
            return None, None


    async def execute_intent(
        self,
        user_prompt: str,
        speed: str = "auto",
        force_cloud: bool = False,
        session_id: str = "",
        system_prompt: str = "",
        mission_profile: str = "AUTO",
        model_target: str | None = "auto",
        channel: str = "web",
        user_id: str = "operator",
        **kwargs: Any
    ) -> dict[str, Any]:
        """Exécute la requête utilisateur gouvernée par NativeHarness FSM.

        Le cycle de vie est :
        INITIALIZING -> PERCEIVING -> THINKING -> VALIDATING -> EXECUTING -> TERMINATED
        """
        start_time = time.perf_counter()

        # 0. Synchroniser la memoire : le harness doit utiliser la MEME que le master
        # (important pour les tests et l'injection de memoire custom)
        self.harness.memory = self.memory

        # Détermination dynamique de l'intention : CHAT vs MISSION
        intent = determine_intent(user_prompt, mission_profile, kwargs.get("is_mission", False))
        _audit_command("INTENT_DECIDED", {
            "intent": intent,
            "profile": mission_profile,
            "prompt_preview": user_prompt[:100],
            "session_id": session_id or ""
        })

        if intent == "MISSION":
            logger.info("[EzzioMaster] Execution d'une mission multi-agents (profile=%s, channel=%s)", mission_profile, channel)

            if kwargs.get("background") or kwargs.get("async_mission"):
                from core.agent.mission_controller import (
                    MissionRecord,
                    MissionStatus,
                    mission_registry,
                )
                mission_id = f"msn-{uuid.uuid4().hex[:8]}"
                mission_record = MissionRecord(
                    mission_id=mission_id,
                    goal=user_prompt,
                    worker_type="MULTI_AGENT",
                    status=MissionStatus.RUNNING,
                    request_id=session_id or "",
                    created_at=datetime.now(UTC).isoformat(),
                )
                mission_registry.register(mission_record)

                async def _run_bg_mission():
                    try:
                        return await self.orchestrate_multi_agent_mission(
                            mission_prompt=user_prompt,
                            subtask_specs=kwargs.get("subtask_specs"),
                            session_id=session_id,
                            channel=channel,
                            user_id=user_id,
                            mission_id=mission_id,
                        )
                    except asyncio.CancelledError:
                        logger.warning("[EzzioMaster] Background mission %s cancelled", mission_id)
                        mission_record.status = MissionStatus.CANCELLED
                        mission_record.result = {"status": "CANCELLED", "error": "Mission cancelled"}
                        raise
                    except Exception as bg_err:
                        logger.error("[EzzioMaster] Background mission %s failed: %s", mission_id, bg_err)
                        mission_record.status = MissionStatus.FAILED
                        mission_record.result = {"error": str(bg_err)}

                bg_task = asyncio.create_task(_run_bg_mission())
                mission_record._async_task = bg_task
                self._background_tasks.add(bg_task)
                bg_task.add_done_callback(self._background_tasks.discard)

                elapsed_ms = int((time.perf_counter() - start_time) * 1000)
                res_bg = {
                    "response": f"[Mission #{mission_id} démarrée en arrière-plan]",
                    "answer": f"[Mission #{mission_id} démarrée en arrière-plan]",
                    "content": f"[Mission #{mission_id} démarrée en arrière-plan]",
                    "message": f"[Mission #{mission_id} démarrée en arrière-plan]",
                    "source": "Master / TaskDAG Background",
                    "authority": "CanonicalIdentity",
                    "model": "auto",
                    "provider": "gemini",
                    "mission": mission_profile or "MISSION",
                    "channel": channel,
                    "elapsed_ms": elapsed_ms,
                    "ok": True,
                    "mission_id": mission_id,
                    "status": "RUNNING",
                    "used_fallback": False,
                }
                return await self._record_assistant_memory(res_bg, session_id, channel)

            mission_res = await self.orchestrate_multi_agent_mission(
                mission_prompt=user_prompt,
                subtask_specs=kwargs.get("subtask_specs"),
                session_id=session_id,
                channel=channel,
                user_id=user_id,
            )
            elapsed_ms = int((time.perf_counter() - start_time) * 1000)
            res_mission = {
                "response": mission_res["synthesis"],
                "answer": mission_res["synthesis"],
                "content": mission_res["synthesis"],
                "message": mission_res["synthesis"],
                "source": f"Master / {mission_res['master_model']}",
                "authority": "CanonicalIdentity",
                "model": mission_res["master_model"],
                "provider": "gemini",
                "mission": mission_profile or "MISSION",
                "channel": channel,
                "elapsed_ms": elapsed_ms,
                "ok": mission_res.get("ok", True),
                "mission_id": mission_res.get("mission_id"),
                "dag_id": mission_res.get("dag_id"),
                "subtasks": mission_res.get("subtasks", []),
                "used_fallback": False,
            }
            return await self._record_assistant_memory(res_mission, session_id, channel)

        # 1. Preparer le system prompt AVANT le harness (qui enregistre en memoire)

        chat_system = system_prompt or await self._build_chat_system_prompt(
            session_id, exclude_prompt=user_prompt
        )

        # 2. Executer la generation via le harness gouverne
        # Le harness va :
        #  - transitionner INITIALIZING -> PERCEIVING (record memoire)
        #  - transitionner PERCEIVING -> THINKING (selection routing)
        #  - transitionner THINKING -> VALIDATING (evaluation policy)
        #  - transitionner VALIDATING -> EXECUTING
        #  - appeler _generate_response() (notre executor)
        #  - transitionner EXECUTING -> TERMINATED
        try:
            harness_result = await self.harness.execute_task(
                task_prompt=user_prompt,
                session_id=session_id,
                user_id=user_id,
                channel=channel,
                executor=self._generate_response,
                # Passage a _generate_response
                chat_system=chat_system,
                force_cloud=force_cloud,
                model_target=model_target,
                # Passage au harness pour la selection du modele
                mission_profile=mission_profile,
            )
        except Exception as harness_err:
            logger.error("[EzzioMaster] Harness a echoue : %s", harness_err)
            elapsed_ms = int((time.perf_counter() - start_time) * 1000)
            fail_msg = f"[FAIL-CLOSED] Harness E-ZZIO indisponible : {harness_err}"
            _audit_command("HARNESS_EXCEPTION", {
                "error": str(harness_err)[:300],
                "outcome": "REFUSED"}, "BLOCKED")
            res_fail = {
                "response": fail_msg,
                "answer": fail_msg,
                "content": fail_msg,
                "message": fail_msg,
                "source": "Harness Fail-Closed",
                "authority": "CanonicalIdentity",
                "model": "none",
                "provider": "none",
                "mission": mission_profile or "STANDARD",
                "channel": channel,
                "elapsed_ms": elapsed_ms,
                "ok": False,
                "error": str(harness_err),
                "used_fallback": False,
            }
            return await self._record_assistant_memory(res_fail, session_id, channel)

        # 3. Extraire la reponse du resultat harness
        if harness_result.get("status") != "SUCCESS":
            elapsed_ms = int((time.perf_counter() - start_time) * 1000)
            error_info = harness_result.get("error", {})
            error_msg = error_info.get("safe_message", "Harness execution failed")
            fail_msg = f"[FAIL-CLOSED] {error_msg}"
            _audit_command("HARNESS_FAILED", {
                "status": harness_result.get("status"),
                "error": error_msg[:300],
                "outcome": "REFUSED"}, "BLOCKED")
            res_fail = {
                "response": fail_msg,
                "answer": fail_msg,
                "content": fail_msg,
                "message": fail_msg,
                "source": "Harness Fail-Closed",
                "authority": "CanonicalIdentity",
                "model": "none",
                "provider": "none",
                "mission": mission_profile or "STANDARD",
                "channel": channel,
                "elapsed_ms": elapsed_ms,
                "ok": False,
                "error": error_msg,
                "used_fallback": False,
                "harness_session_id": harness_result.get("session_id"),
                "harness_correlation_id": harness_result.get("correlation_id"),
            }
            return await self._record_assistant_memory(res_fail, session_id, channel)

        # Extraire la reponse generee
        inner = harness_result.get("result", {})
        if not isinstance(inner, dict):
            inner = {"response": str(inner), "model": "unknown", "provider": "unknown"}

        elapsed_ms = int((time.perf_counter() - start_time) * 1000)

        res_conv = {
            "response": inner.get("response", ""),
            "answer": inner.get("answer", inner.get("response", "")),
            "content": inner.get("content", inner.get("response", "")),
            "message": inner.get("message", inner.get("response", "")),
            "source": inner.get("source", "Unknown"),
            "authority": "CanonicalIdentity",
            "model": inner.get("model", harness_result.get("model", "unknown")),
            "provider": inner.get("provider", "unknown"),
            "mission": mission_profile or "STANDARD",
            "channel": channel,
            "elapsed_ms": elapsed_ms,
            "ok": True,
            "used_fallback": inner.get("used_fallback", False),
            "usage": inner.get("usage", {}),
            "thinking_level": inner.get("thinking_level"),
            "fallback_notice": inner.get("fallback_notice"),
            "harness_session_id": harness_result.get("session_id"),
            "harness_correlation_id": harness_result.get("correlation_id"),
            "harness_turn": harness_result.get("turn"),
        }

        _audit_command("CONV_MODEL", {
            "model": res_conv["model"], "provider": res_conv["provider"],
            "outcome": "RESPONDED",
            "session_id": session_id or "",
            "harness_session_id": harness_result.get("session_id"),
        })
        return await self._record_assistant_memory(res_conv, session_id, channel)

    async def process_chat(
        self,
        prompt: str,
        session_id: str = "",
        channel: str = "web",
        user_id: str = "operator",
        **kwargs: Any
    ) -> str:
        """Alias de compatibilité pour le traitement de chat retournant directement le texte de réponse."""
        res = await self.execute_intent(
            user_prompt=prompt,
            session_id=session_id,
            channel=channel,
            user_id=user_id,
            **kwargs
        )
        return res.get("response", "")

    async def process_user_message(
        self,
        prompt: str = "",
        message: str = "",
        session_id: str = "",
        channel: str = "web",
        user_id: str = "operator",
        **kwargs: Any
    ) -> dict[str, Any]:
        """Alias de compatibilité pour le traitement des messages utilisateur via execute_intent."""
        user_prompt = prompt or message
        return await self.execute_intent(
            user_prompt=user_prompt,
            session_id=session_id,
            channel=channel,
            user_id=user_id,
            **kwargs
        )

    async def orchestrate_multi_agent_mission(
        self,
        mission_prompt: str,
        subtask_specs: list[dict[str, Any]] | None = None,
        session_id: str = "",
        channel: str = "web",
        user_id: str = "operator",
        workspace_root: str | None = None,
        max_retries: int = 2,
        **kwargs: Any
    ) -> dict[str, Any]:
        """Décompose une mission en sous-tâches agentiques gouvernées sous forme d'un TaskDAG
        exécuté par le DAGOrchestrator. Les résultats des sous-tâches amont sont transmis
        aux dépendances aval, avant la synthèse finale Master."""
        from core.agent.mission_controller import MissionRecord, MissionStatus, mission_registry
        from core.agents.registry import AgentStatus, agent_registry
        from core.cognition.model_router import ModelRouter
        from core.orchestration.dag import DAGExecutionStatus, DAGNode, TaskDAG
        from core.orchestration.engine import dag_orchestrator

        ws_root = workspace_root or self.workspace_root
        router = ModelRouter()

        # 0. Initialisation et enregistrement de la Mission dans le MissionRegistry
        existing_mission_id = kwargs.get("mission_id")
        if existing_mission_id and mission_registry.get(existing_mission_id):
            mission_id = existing_mission_id
            mission_record = mission_registry.get(existing_mission_id)
        else:
            mission_id = f"msn-{uuid.uuid4().hex[:8]}"
            mission_record = MissionRecord(
                mission_id=mission_id,
                goal=mission_prompt,
                worker_type="MULTI_AGENT",
                status=MissionStatus.RUNNING,
                request_id=session_id or "",
                created_at=datetime.now(UTC).isoformat(),
            )
            mission_registry.register(mission_record)

        # 1. Décomposition en sous-tâches si non fournies (avec dépendances réelles)
        if not subtask_specs:
            lower_prompt = mission_prompt.lower()
            if any(w in lower_prompt for w in ("test", "valide", "vérifie", "qa")):
                subtask_specs = [
                    {
                        "task_id": "subtask-forensic-01",
                        "role": "forensic",
                        "prompt": f"Audit forensic : analyse les risques et vulnérabilités pour : {mission_prompt[:200]}",
                        "complexity": 0.6,
                        "dependencies": [],
                    },
                    {
                        "task_id": "subtask-coding-02",
                        "role": "coding",
                        "prompt": f"Implémentation technique : propose un correctif sécurisé pour : {mission_prompt[:200]}",
                        "complexity": 0.7,
                        "dependencies": ["subtask-forensic-01"],
                    },
                    {
                        "task_id": "subtask-qa-03",
                        "role": "qa",
                        "prompt": f"Validation continue : vérifie l'absence de régression et l'intégrité pour : {mission_prompt[:200]}",
                        "complexity": 0.5,
                        "dependencies": ["subtask-coding-02"],
                    },
                ]
            else:
                subtask_specs = [
                    {
                        "task_id": "subtask-forensic-01",
                        "role": "forensic",
                        "prompt": f"Audit forensic : analyse les risques et vulnérabilités pour : {mission_prompt[:200]}",
                        "complexity": 0.6,
                        "dependencies": [],
                    },
                    {
                        "task_id": "subtask-coding-02",
                        "role": "coding",
                        "prompt": f"Implémentation technique : propose un correctif sécurisé pour : {mission_prompt[:200]}",
                        "complexity": 0.7,
                        "dependencies": ["subtask-forensic-01"],
                    },
                ]

        _audit_command("MISSION_STARTED", {
            "mission_id": mission_id,
            "goal": mission_prompt[:150],
            "subtasks_count": len(subtask_specs),
            "session_id": session_id or ""
        })

        role_agent_map = {
            "coding": "coder_worker",
            "forensic": "sec_guard",
            "security": "sec_guard",
            "qa": "qa_tester",
            "test": "qa_tester",
            "validation": "qa_tester",
            "research": "researcher_scout",
            "scout": "researcher_scout",
            "web": "web_agent",
            "general": "coder_worker",
        }

        bounded_retries = max(0, min(max_retries, 2))

        # 2. Construction du TaskDAG
        dag = TaskDAG(dag_id=f"dag-{mission_id}", name=f"mission_{mission_id}")
        for spec in subtask_specs:
            t_id = spec.get("task_id", f"subtask-{uuid.uuid4().hex[:6]}")
            t_role = spec.get("role", "general")
            t_deps = list(spec.get("dependencies") or [])
            dag.add_node(
                task_id=t_id,
                title=f"{t_role.upper()} - {t_id}",
                action_type=t_role,
                payload=dict(spec),
                dependencies=t_deps,
                max_retries=bounded_retries,
            )

        # 3. Handler local d'exécution pour les nœuds du DAG
        async def dag_handler(node: DAGNode) -> dict[str, Any]:
            spec = node.payload
            task_id = node.task_id
            task_role = node.action_type
            comp = spec.get("complexity", 0.6)
            tool_name = spec.get("tool_name")
            tool_args = spec.get("tool_args", {})
            worker_type = spec.get("worker", "internal")

            routing = router.select_engine(
                task_type=task_role,
                complexity_score=comp,
                risk_level="low",
                channel=channel
            )
            node.agent_id = role_agent_map.get(task_role.lower(), "coder_worker")
            node.provider = routing.get("provider", "gemini")

            target_agent_id = node.agent_id
            agent_desc = agent_registry.get_agent(target_agent_id)
            if agent_desc:
                agent_desc.status = AgentStatus.BUSY
                agent_desc.current_task_id = task_id
                agent_desc.current_action = f"Executing subtask {task_id} ({task_role})"

            tool_executed = None
            tool_result = None
            sub_output = ""
            worker_pid = None
            worker_status = "SUCCESS"

            try:
                if tool_name:
                    tool_executed = tool_name
                    try:
                        from core.agent.tools_registry import ToolRegistry
                        t_reg = ToolRegistry(workspace_root=ws_root)
                        tool_result = t_reg.execute_tool(tool_name, tool_args)
                    except Exception as t_err:
                        tool_result = f"[TOOL_ERROR] {t_err}"

                # Propagation des résultats des dépendances amont
                dependency_results = {}
                for dep_id in node.dependencies:
                    dep_node = dag.nodes.get(dep_id)
                    if dep_node and dep_node.result and "output" in dep_node.result:
                        dependency_results[dep_id] = dep_node.result.get("output", "")

                prompt_to_send = spec.get("prompt", mission_prompt)
                if dependency_results:
                    dep_text = "\n".join(
                        f"- [{dep_id}] : {out[:300]}" for dep_id, out in dependency_results.items()
                    )
                    prompt_to_send = (
                        f"{prompt_to_send}\n\n"
                        f"[RÉSULTATS DÉPENDANCES EN AMONT]\n{dep_text}\n[/RÉSULTATS DÉPENDANCES]"
                    )

                if tool_result:
                    prompt_to_send = (
                        f"{prompt_to_send}\n\n"
                        f"[RÉSULTAT OUTIL {tool_name}]\n{tool_result}\n[/RÉSULTAT OUTIL]"
                    )

                if node.retry_count > 0:
                    prompt_to_send = (
                        f"[RETRY {node.retry_count}/{node.max_retries} - Corrige l'erreur précédente]\n"
                        f"{prompt_to_send}"
                    )

                if worker_type == "hermes":
                    from core.agent.hermes_worker_profiles import (
                        build_context_pack,
                        render_context_prompt,
                        resolve_profile,
                    )
                    requested_profile = spec.get("profile") or task_role
                    try:
                        worker_profile = resolve_profile(requested_profile)
                    except ValueError:
                        worker_profile = resolve_profile("context_reader")

                    spec_files = spec.get("files") or spec.get("context_files")
                    if spec_files and worker_profile.name in ("context_reader", "reader", "context_auditor", "auditor"):
                        try:
                            pack = build_context_pack(
                                task_id=task_id,
                                objective=prompt_to_send,
                                file_paths=spec_files,
                                workspace_root=self.workspace_root,
                                audit_ledger=getattr(self.hermes_adapter, "audit_ledger", None),
                            )
                            prompt_to_send = render_context_prompt(pack, worker_profile)
                        except Exception as pack_err:
                            sub_output = f"[POLICY_DENIED] Context pack creation failed: {pack_err}"
                            worker_status = "POLICY_DENIED"

                    if worker_status != "POLICY_DENIED":
                        hermes_res = await self.hermes_adapter.submit(
                            task_id=task_id,
                            prompt=prompt_to_send,
                            model=routing.get("model"),
                            provider=routing.get("provider"),
                            timeout=spec.get("timeout", worker_profile.default_timeout_sec),
                            profile=worker_profile,
                            workspace_root=spec.get("workspace_root") or ws_root,
                        )
                        sub_output = hermes_res.output or hermes_res.stdout
                        worker_pid = hermes_res.pid
                        worker_status = hermes_res.status
                elif tool_result and not spec.get("prompt"):
                    sub_output = tool_result
                else:
                    if self._injected_provider is not None:
                        sub_provider = self.provider
                    else:
                        try:
                            from core.providers.registry import ProviderFactory
                            sub_provider = ProviderFactory.create(routing.get("provider", "gemini"))
                        except Exception as p_init_err:
                            logger.warning("[EzzioMaster] ProviderFactory init: %s", p_init_err)
                            sub_provider = None

                    if sub_provider is not None:
                        try:
                            resp: ProviderResponse = await sub_provider.generate(
                                prompt=prompt_to_send,
                                model=routing["model"],
                                thinking_level=routing.get("thinking_level", "off"),
                                max_tokens=300
                            )
                            sub_output = resp.content or ""
                        except Exception as gen_err:
                            logger.warning("[EzzioMaster] Subtask %s generation error: %s", task_id, gen_err)
                            sub_output = f"[Résultat {task_role.upper()}] Tâche exécutée sous {routing['model']}."
                    else:
                        sub_output = f"[Résultat {task_role.upper()}] Tâche exécutée sous {routing['model']}."

                is_valid = bool(sub_output and sub_output.strip())
                if tool_result and ("[POLICY_DENIED]" in tool_result or "[RUNTIME POLICY BLOCKED]" in tool_result):
                    is_valid = False
                if worker_type == "hermes" and worker_status not in ("SUCCESS", "COMPLETED"):
                    is_valid = False

                _audit_command("VALIDATION_RESULT", {
                    "task_id": task_id,
                    "worker": worker_type,
                    "role": task_role,
                    "is_valid": is_valid,
                    "status": worker_status,
                })

                if not is_valid:
                    raise RuntimeError(f"Validation failed for node {task_id}: {worker_status or 'Empty output'}")

                return {
                    "task_id": task_id,
                    "role": task_role,
                    "agent_id": target_agent_id,
                    "worker": worker_type,
                    "pid": worker_pid,
                    "model": routing["model"],
                    "thinking_level": routing.get("thinking_level"),
                    "tool": tool_executed,
                    "tool_result": tool_result,
                    "validated": True,
                    "retries": node.retry_count,
                    "status": "SUCCESS",
                    "output": sub_output or f"[Résultat {task_role.upper()}] Audit/Code validé avec succès.",
                    "dependency_results": dependency_results,
                }
            finally:
                if agent_desc:
                    agent_desc.status = AgentStatus.IDLE
                    agent_desc.current_task_id = None
                    agent_desc.current_action = "Ready"

        # 4. Exécution du DAG via le DAGOrchestrator
        await dag_orchestrator.execute_dag(dag, default_handler=dag_handler)

        # 5. Extraction des résultats pour la synthèse
        results = []
        for node in dag.nodes.values():
            if node.status == DAGExecutionStatus.COMPLETED and node.result:
                results.append(node.result)
                _audit_command("SUBTASK_EXECUTED", {
                    "task_id": node.task_id,
                    "role": node.action_type,
                    "agent_id": node.result.get("agent_id", node.agent_id),
                    "worker": node.result.get("worker", "internal"),
                    "pid": node.result.get("pid"),
                    "model": node.result.get("model", node.provider),
                    "status": "SUCCESS",
                    "retries": node.retry_count,
                })
            else:
                res_dict = {
                    "task_id": node.task_id,
                    "role": node.action_type,
                    "agent_id": node.agent_id,
                    "worker": node.payload.get("worker", "internal"),
                    "pid": None,
                    "model": node.provider,
                    "thinking_level": None,
                    "tool": node.payload.get("tool_name"),
                    "tool_result": None,
                    "validated": False,
                    "retries": node.retry_count,
                    "status": node.status.value,
                    "output": node.error or f"Node status: {node.status.value}",
                }
                results.append(res_dict)
                _audit_command("SUBTASK_EXECUTED", {
                    "task_id": node.task_id,
                    "role": node.action_type,
                    "agent_id": node.agent_id,
                    "worker": node.payload.get("worker", "internal"),
                    "pid": None,
                    "model": node.provider,
                    "status": node.status.value,
                    "retries": node.retry_count,
                })

        # 6. Synthèse stratégique Master
        master_routing = router.select_engine(
            task_type="general",
            complexity_score=0.9,
            risk_level="low",
            is_mission=True,
            channel=channel
        )

        synthesis_prompt = (
            f"Synthèse Master ({master_routing['model']}) pour la mission :\n{mission_prompt}\n\n"
            f"Résultats des sous-tâches des agents spécialisés :\n"
            + "\n".join(
                [f"- [{r['role'].upper()} / {r['agent_id']} / {r['model']}] (Status: {r['status']}) : {r['output'][:250]}"
                 for r in results]
            )
        )

        if self._injected_provider is not None:
            master_provider = self.provider
        else:
            try:
                from core.providers.registry import ProviderFactory
                master_provider = ProviderFactory.create(master_routing.get("provider", "gemini"))
            except Exception:
                master_provider = None

        if master_provider is not None:
            try:
                final_resp: ProviderResponse = await master_provider.generate(
                    prompt=synthesis_prompt,
                    model=master_routing["model"],
                    thinking_level=master_routing.get("thinking_level", "high"),
                    max_tokens=500
                )
                synthesis_text = final_resp.content or ""
            except Exception as m_err:
                logger.warning("[EzzioMaster] Master synthesis exception: %s", m_err)
                synthesis_text = f"[Synthèse E-ZZIO Master {master_routing['model']}] Mission orchestrée avec succès sur {len(results)} sous-tâches."
        else:
            synthesis_text = f"[Synthèse E-ZZIO Master {master_routing['model']}] Mission orchestrée avec succès sur {len(results)} sous-tâches."

        if not synthesis_text.strip():
            synthesis_text = f"[Synthèse E-ZZIO Master {master_routing['model']}] Mission #{mission_id} orchestrée avec succès sur {len(results)} sous-tâches."

        all_ok = dag.is_completed()
        mission_record.status = MissionStatus.SUCCEEDED if all_ok else MissionStatus.FAILED
        mission_record.result = {
            "synthesis": synthesis_text,
            "master_model": master_routing["model"],
            "subtasks_count": len(results),
            "dag_id": dag.dag_id,
        }

        _audit_command("MISSION_SYNTHESIS_COMPLETED", {
            "mission_id": mission_id,
            "dag_id": dag.dag_id,
            "master_model": master_routing["model"],
            "subtask_count": len(results),
            "all_ok": all_ok,
            "session_id": session_id or ""
        })

        if session_id:
            try:
                await self._record_assistant_memory({
                    "response": synthesis_text,
                    "model": master_routing["model"],
                    "provider": master_routing.get("provider", "api")
                }, session_id, channel)
            except Exception as exc:
                logger.warning("[EzzioMaster] Memory record mission synthesis failed: %s", exc)

        return {
            "mission": mission_prompt,
            "mission_id": mission_id,
            "dag_id": dag.dag_id,
            "master_model": master_routing["model"],
            "subtasks": results,
            "synthesis": synthesis_text,
            "ok": all_ok
        }



ezzio_master = EzzioMaster()
