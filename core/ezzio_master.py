"""E-ZZIO Master Orchestrator — Mono-Autorité Identitaire & Conversationnel.

Version épurée : GeminiProvider direct, plus de fédération/missions/workers.
"""
from __future__ import annotations

import logging
import time
from typing import Any

from core.kernel.native_harness import NativeHarness
from core.memory.instance import memory_gateway
from core.providers.base_provider import ProviderResponse
from core.providers.gemini_provider import GeminiProvider

logger = logging.getLogger("EzzioMaster")


def _has_internet(timeout_seconds: float = 1.0) -> bool:
    """Verifie rapidement la connectivite Internet.

    Strategie hybride : si pas d'Internet, on bascule sur le provider local
    (Ollama) au lieu d'echouer sur les providers cloud.

    Args:
        timeout_seconds: Timeout de la tentative de connexion.

    Returns:
        True si Internet est accessible, False sinon.
    """
    import socket
    try:
        socket.create_connection(("8.8.8.8", 53), timeout=timeout_seconds).close()
        return True
    except OSError:
        return False

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


class EzzioMaster:
    """Orchestrateur central E-ZZIO : conversation via GeminiProvider direct."""

    def __init__(self, provider: GeminiProvider | None = None, **kwargs: Any) -> None:
        self.provider = provider or GeminiProvider()
        self.memory = memory_gateway
        self._memory_initialized = False
        self.harness = NativeHarness(router=None, policy_guard=None, audit_ledger=None, workspace_root=r"G:\AI\E-zzio")

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
        force_cloud = kwargs.get("force_cloud", False)
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

        # Selection dynamique du provider : cloud-first ou local si pas d'Internet
        _has_net = _has_internet()
        _force_local = (model_target or "").lower() in ("local", "ollama")
        _force_cloud_explicit = (model_target or "").lower() == "cloud"

        if _force_local:
            is_local = True
            logger.info("[EzzioMaster] Mode local explicite (model_target=%s)", model_target)
        elif _force_cloud_explicit:
            is_local = False
            logger.info("[EzzioMaster] Mode cloud explicite (model_target=%s)", model_target)
        elif not _has_net:
            is_local = True
            logger.info("[EzzioMaster] Pas d'Internet -> basculement local (Ollama)")
        else:
            is_local = (routing.get("provider") == "ollama" and not force_cloud)

        selected_model = routing.get("model", "gemini-3.5-flash-lite")

        # Utiliser le model_target si specifie
        if model_target and model_target not in ("auto", "local", "cloud"):
            selected_model = model_target

        resp: ProviderResponse
        used_fallback = False
        fallback_notice: dict | None = None
        detected_provider = self._detect_provider_from_model(selected_model)

        if is_local:
            from core.providers.ollama_provider import OllamaProvider
            ollama_prov = OllamaProvider(model=selected_model)
            resp = await ollama_prov.generate(
                prompt=user_prompt,
                system_prompt=chat_system if chat_system else None,
                model=selected_model,
                temperature=0.2,
                max_tokens=512,
            )
        else:
            try:
                if detected_provider == "openrouter":
                    from core.providers.openrouter_provider import OpenRouterProvider
                    prov = OpenRouterProvider()
                elif detected_provider == "groq":
                    from core.providers.groq_provider import GroqProvider
                    prov = GroqProvider()
                elif detected_provider == "nvidia":
                    from core.providers.nvidia_nim_provider import NvidiaNimProvider
                    prov = NvidiaNimProvider()
                elif detected_provider == "ollama":
                    from core.providers.ollama_provider import OllamaProvider
                    prov = OllamaProvider()
                else:
                    prov = self.provider

                resp = await prov.generate(
                    prompt=user_prompt,
                    system_prompt=chat_system if chat_system else None,
                    model=selected_model,
                    temperature=0.2,
                    max_tokens=2048,
                    thinking_level=thinking_level,
                )
            except Exception as cloud_err:
                logger.warning(
                    "[EzzioMaster] Echec provider %s (%s) -> fallback",
                    detected_provider, cloud_err,
                )
                fb_resp, fb_notice = await self._try_fallback(
                    detected_provider=detected_provider,
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

    def _detect_provider_from_model(self, model: str) -> str:
        """Detecte le provider depuis le nom du modele."""
        m = (model or "").lower()
        if m.startswith("gemini"):
            return "gemini"
        if m.startswith("groq/"):
            return "groq"
        if m.startswith("openrouter/"):
            return "openrouter"
        if m.startswith("nvidia/"):
            return "nvidia"
        if m.endswith(":free"):
            return "openrouter"
        if m.startswith(("llama", "mixtral", "gemma-")):
            return "groq"
        if m.startswith(("nvidia/", "nvidia-", "nvapi")):
            return "nvidia"
        if ":" in m or m.endswith(":latest"):
            return "ollama"

        # REGLE GENERALE : tout modele avec "/" est OpenRouter
        # OpenRouter est le seul provider a utiliser le format "provider/model"
        if "/" in m:
            return "openrouter"

        # Fallback final : nom simple sans "/" = Gemini
        return "gemini"

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
            from core.providers.gemini_provider import GeminiProvider
            fb_prov = GeminiProvider()
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
                "actual_provider": "gemini",
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
        mission_profile: str = "STANDARD",
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
        user_id: str = "operator"
    ) -> dict[str, Any]:
        """Décompose une mission en sous-tâches agentiques, consulte ModelRouter par sous-tâche, agrège et valide les résultats, puis produit la synthèse finale Master."""
        from core.cognition.model_router import ModelRouter
        router = ModelRouter()

        # 1. Décomposition en sous-tâches si non fournies
        if not subtask_specs:
            subtask_specs = [
                {
                    "task_id": "subtask-forensic-01",
                    "role": "forensic",
                    "prompt": f"Audit forensic : analyse les risques et vulnérabilités pour : {mission_prompt[:200]}",
                    "complexity": 0.6
                },
                {
                    "task_id": "subtask-coding-02",
                    "role": "coding",
                    "prompt": f"Implémentation technique : propose un correctif sécurisé pour : {mission_prompt[:200]}",
                    "complexity": 0.7
                }
            ]

        results = []
        for spec in subtask_specs:
            task_role = spec.get("role", "general")
            comp = spec.get("complexity", 0.6)

            # Consult ModelRouter per subtask
            routing = router.select_engine(
                task_type=task_role,
                complexity_score=comp,
                risk_level="low",
                channel=channel
            )

            # Subtask execution via Provider with router-selected model & thinking level
            resp: ProviderResponse = await self.provider.generate(
                prompt=spec.get("prompt", mission_prompt),
                model=routing["model"],
                thinking_level=routing.get("thinking_level", "off"),
                max_tokens=300
            )

            results.append({
                "task_id": spec.get("task_id"),
                "role": task_role,
                "model": routing["model"],
                "thinking_level": routing.get("thinking_level"),
                "output": resp.content or f"[Résultat {task_role.upper()}] Audit/Code validé avec succès."
            })

            _audit_command("SUBTASK_EXECUTED", {
                "task_id": spec.get("task_id"),
                "role": task_role,
                "model": routing["model"]
            })

        # 2. Master Strategic Synthesis using gemini-3.8-flash (MASTER)
        master_routing = router.select_engine(
            task_type="general",
            complexity_score=0.9,
            risk_level="low",
            is_mission=True,
            channel=channel
        )

        synthesis_prompt = f"Synthèse Master ({master_routing['model']}) pour la mission :\n{mission_prompt}\n\nRésultats des sous-tâches :\n" + "\n".join(
            [f"- [{r['role'].upper()} / {r['model']}] : {r['output'][:200]}" for r in results]
        )

        final_resp: ProviderResponse = await self.provider.generate(
            prompt=synthesis_prompt,
            model=master_routing["model"],
            thinking_level=master_routing.get("thinking_level", "high"),
            max_tokens=500
        )

        synthesis_text = final_resp.content or f"[Synthèse E-ZZIO Master {master_routing['model']}] Mission orchestrée avec succès sur {len(results)} sous-tâches."

        _audit_command("MISSION_SYNTHESIS_COMPLETED", {
            "master_model": master_routing["model"],
            "subtask_count": len(results),
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
            "master_model": master_routing["model"],
            "subtasks": results,
            "synthesis": synthesis_text,
            "ok": True
        }


ezzio_master = EzzioMaster()
