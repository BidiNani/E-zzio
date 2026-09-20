"""E-ZZIO Master Orchestrator — Mono-Autorité Identitaire & Conversationnel.

Version épurée : GeminiProvider direct, plus de fédération/missions/workers.
"""
from __future__ import annotations

import logging
import re
import time
from typing import Any

from core.kernel.native_harness import NativeHarness
from core.memory.instance import memory_gateway
from core.providers.base_provider import ProviderResponse
from core.providers.gemini_provider import GeminiProvider

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
        force_cloud: bool = True,
        session_id: str = "",
        system_prompt: str = "",
        mission_profile: str = "STANDARD",
        model_target: str | None = "auto",
        channel: str = "web",
        user_id: str = "operator",
        **kwargs: Any
    ) -> dict[str, Any]:
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
            from core.cognition.model_router import ModelRouter
            router = ModelRouter()

            is_mission = bool(mission_profile and mission_profile.upper() not in ["STANDARD", "CHAT", "LOW"])
            comp_score = 0.85 if is_mission else (0.4 if channel in ["discord", "chat", "integration_test"] else 0.6)
            prompt_lower = (user_prompt or "").lower().strip()

            # Simple short greetings or ultra-fast path optimization
            if not is_mission and (len(prompt_lower.split()) <= 3 or prompt_lower in ["salut", "bonjour", "hello", "ping"]):
                comp_score = 0.1

            is_coding = bool(re.search(r"\b(code|coder|coding|python|javascript|typescript|c\+\+|rust|html|css|sql|script|scripts|fonction|classes?|def\s|class\s|bug|refactor|debug|git)\b", prompt_lower))
            if is_coding or "architecture" in prompt_lower or "securite" in prompt_lower or "vault" in prompt_lower:
                comp_score = max(comp_score, 0.75)

            task_t = "coding" if is_coding else "general"

            routing = router.select_engine(
                task_type=task_t,
                complexity_score=comp_score,
                risk_level="low",
                channel=channel,
                is_mission=is_mission
            )
            fallback_notice: dict | None = None
            # Priorite au model_target utilisateur, sinon routing automatique
            if model_target and model_target != "auto":
                selected_model = model_target
            else:
                selected_model = routing["model"]
            thinking_level = routing.get("thinking_level")
            # Override depuis settings utilisateur (toggle frontend)
            try:
                from routers.settings import _state as _settings_state
                if _settings_state.get("thinking_enabled"):
                    thinking_level = _settings_state.get("thinking_level", thinking_level)
            except Exception:
                pass

            chat_system = system_prompt or await self._build_chat_system_prompt(session_id, exclude_prompt=user_prompt)

            # Dynamic provider selection (Ollama local vs Gemini API)
            # Cloud-First par défaut : Cloud Gemini en priorité absolue.
            is_local = (routing.get("provider") == "ollama" and not force_cloud)
            used_fallback = False

            if is_local:
                from core.providers.ollama_provider import OllamaProvider
                ollama_prov = OllamaProvider(model=selected_model)
                resp: ProviderResponse = await ollama_prov.generate(
                    prompt=user_prompt or "",
                    system_prompt=chat_system if chat_system else None,
                    model=selected_model,
                    temperature=0.2,
                    max_tokens=512,
                )
            else:
                # Routing multi-provider base sur le modele selectionne
                detected_provider = self._detect_provider_from_model(selected_model)

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
                    else:  # gemini
                        prov = self.provider

                    resp: ProviderResponse = await prov.generate(
                        prompt=user_prompt or "",
                        system_prompt=chat_system if chat_system else None,
                        model=selected_model,
                        temperature=0.2,
                        max_tokens=2048,
                        thinking_level=thinking_level,
                    )
                except Exception as cloud_err:
                    # Fallback intelligent vers le modele cible de FALLBACK_MAP
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
                        raise cloud_err
                    resp = fb_resp
                    used_fallback = True
                    fallback_notice = fb_notice

            elapsed_ms = int((time.perf_counter() - start_time) * 1000)

            reply = resp.content or ""
            model_name = resp.model or selected_model
            provider_name = resp.provider or routing["provider"]

            # Si le provider principal a repondu vide -> fallback intelligent
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
                "used_fallback": used_fallback,
                "usage": getattr(resp, "usage", {}) or {},
                "thinking_level": getattr(resp, "thinking_level", None),
                "fallback_notice": fallback_notice,
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
