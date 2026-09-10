"""E-ZZIO Master Orchestrator — Mono-Autorité Identitaire, Conversationnel & Workers Asynchrones."""
from __future__ import annotations
import re
import uuid
import time
import asyncio
import logging
from datetime import datetime, timezone
from typing import Any, Dict, Optional, List

from core.agent.coder_federation import (
    CoderModelFederationRouter,
    coder_federation_router,
    TaskProfile,
    TaskComplexity,
    ContextSize,
    LatencyClass,
    PrivacyRequirement,
    TaskType,
)
from core.agent.mission_controller import (
    MissionRecord,
    MissionStatus,
    mission_registry,
)
from core.agent.worker_fleet import worker_fleet
from core.agents.registry import agent_registry
from core.memory.instance import memory_gateway
from core.providers.base_provider import ProviderResponse

logger = logging.getLogger("EzzioMaster")

_command_ledger = None


def _audit_command(action: str, payload: Dict[str, Any],
                   status: str = "SUCCESS") -> None:
    """Chaîne d'audit des commandes (§22) : ledger scellé, jamais bloquant.
    Un échec d'audit n'interrompt jamais le dispatch (warning seul)."""
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


# Politique L0 d'autorisation outils par famille de worker (least privilege).
# Miroir de ToolRegistry.list_tools — parité imposée par test.
_KNOWN_TOOL_NAMES = (
    "get_codebase_map", "grep_codebase", "find_files", "read_file",
    "read_file_slice", "write_file", "apply_patch", "run_test_file",
    "run_powershell", "code_analyzer",
)
_WORKER_TOOL_AUTH = {
    "RESEARCH_WORKER": ("get_codebase_map", "grep_codebase", "find_files",
                        "read_file", "read_file_slice"),
    "WEB_WORKER": ("read_file", "read_file_slice"),
    "MODEL_WORKER": ("get_codebase_map", "read_file"),
    "CODER_WORKER": ("get_codebase_map", "grep_codebase", "find_files",
                     "read_file", "read_file_slice", "write_file",
                     "apply_patch", "run_test_file", "code_analyzer"),
    "FILE_WORKER": ("find_files", "read_file", "read_file_slice", "write_file"),
    "DATA_WORKER": ("read_file", "read_file_slice", "write_file"),
    "AUTOMATION_WORKER": ("read_file", "write_file", "run_powershell"),
    "QA_WORKER": ("read_file", "read_file_slice", "grep_codebase",
                  "run_test_file"),
    "SYSTEM_WORKER": ("get_codebase_map", "read_file", "run_powershell"),
    "SECURITY_WORKER": ("get_codebase_map", "grep_codebase", "read_file",
                        "code_analyzer"),
    "DOCUMENT_WORKER": ("read_file", "read_file_slice", "write_file"),
    "IMAGE_WORKER": (),
    "CLEANING_WORKER": ("find_files", "read_file"),
}
# Aliases _AGENT héritent de la famille _WORKER correspondante.
for _alias, _base in (("CODER_AGENT", "CODER_WORKER"),
                      ("RESEARCH_AGENT", "RESEARCH_WORKER"),
                      ("WEB_AGENT", "WEB_WORKER"),
                      ("SYSTEM_AGENT", "SYSTEM_WORKER"),
                      ("CLEANING_AGENT", "CLEANING_WORKER"),
                      ("FILE_AGENT", "FILE_WORKER"),
                      ("IMAGE_AGENT", "IMAGE_WORKER"),
                      ("DOCUMENT_AGENT", "DOCUMENT_WORKER"),
                      ("QA_AGENT", "QA_WORKER"),
                      ("SECURITY_AGENT", "SECURITY_WORKER"),
                      ("MODEL_AGENT", "MODEL_WORKER"),
                      ("DATA_AGENT", "DATA_WORKER"),
                      ("AUTOMATION_AGENT", "AUTOMATION_WORKER")):
    _WORKER_TOOL_AUTH[_alias] = _WORKER_TOOL_AUTH[_base]


KNOWN_MODEL_TARGETS = frozenset({
    "auto",
    "",
    "ollama",
    "ollama_qwen",
    "local",
    "gemini",
    "gemini_cloud",
})


class UnknownModelTargetError(ValueError):
    """Target modèle explicitement demandé mais inconnu du registre (Fail-Closed)."""
    pass


class GovernanceError(RuntimeError):
    """Refus de gouvernance : fédération vide/épuisée, aucun secours hors registre."""
    pass


class EzzioMaster:
    """Orchestrateur central E-ZZIO : Master conversationnel immédiat + Workers asynchrones."""

    def __init__(self, federation_router: Optional[CoderModelFederationRouter] = None) -> None:
        self.federation_router = federation_router or coder_federation_router
        self.fleet = worker_fleet
        self.registry = mission_registry
        self.agent_registry = agent_registry
        self.memory = memory_gateway
        self._memory_initialized = False

    def _resolve_task_profile(
        self,
        mission_profile: str = "STANDARD",
        model_target: Optional[str] = "auto",
        speed: str = "auto",
        force_cloud: bool = False,
    ) -> TaskProfile:
        """Mappe les paramètres utilisateur en profil de tâche formel pour la fédération."""
        profile_key = (mission_profile or "STANDARD").upper().strip()
        target = (model_target or "auto").lower().strip()

        # Target explicitement demandé mais inconnu : rejet Fail-Closed, jamais d'inférence silencieuse.
        if target not in KNOWN_MODEL_TARGETS:
            raise UnknownModelTargetError(
                f"[FAIL-CLOSED] Target modèle inconnu : '{model_target}'. "
                f"Targets autorisés : {sorted(KNOWN_MODEL_TARGETS - {'', 'auto'})} ou 'auto'."
            )

        # 1. Traitement prioritaire du confinement souverain
        if profile_key == "LOCAL_ONLY" or target in ("ollama", "ollama_qwen", "local"):
            return TaskProfile(
                complexity=TaskComplexity.STANDARD,
                context_size=ContextSize.NORMAL,
                latency_class=LatencyClass.MEDIUM,
                multimodal=False,
                privacy_required=PrivacyRequirement.LOCAL_ONLY,
                task_type=TaskType.CODING,
            )

        # 2. Profils explicites de mission
        if profile_key == "FAST" or speed == "fast" and profile_key not in ("COMPLEX", "CRITICAL"):
            return TaskProfile(
                complexity=TaskComplexity.SIMPLE,
                context_size=ContextSize.NORMAL,
                latency_class=LatencyClass.HIGH,
                multimodal=False,
                privacy_required=PrivacyRequirement.CLOUD_ALLOWED,
                task_type=TaskType.CODING,
            )

        if profile_key in ("COMPLEX", "CRITICAL"):
            return TaskProfile(
                complexity=TaskComplexity.COMPLEX if profile_key != "CRITICAL" else TaskComplexity.CRITICAL,
                context_size=ContextSize.NORMAL,
                latency_class=LatencyClass.MEDIUM,
                multimodal=False,
                privacy_required=PrivacyRequirement.CLOUD_ALLOWED,
                task_type=TaskType.CODING,
            )

        if profile_key in ("CONTEXT", "MULTIMODAL") or target in ("gemini", "gemini_cloud"):
            return TaskProfile(
                complexity=TaskComplexity.STANDARD,
                context_size=ContextSize.LARGE,
                latency_class=LatencyClass.MEDIUM,
                multimodal=True if profile_key == "MULTIMODAL" else False,
                privacy_required=PrivacyRequirement.CLOUD_ALLOWED,
                task_type=TaskType.CODING,
            )

        # 3. Profil standard par défaut (Free-first / Local-preferred)
        # Voie conversationnelle du Master : type CHAT (Hermes local).
        privacy = PrivacyRequirement.CLOUD_ALLOWED if force_cloud else PrivacyRequirement.LOCAL_PREFERRED
        return TaskProfile(
            complexity=TaskComplexity.STANDARD,
            context_size=ContextSize.NORMAL,
            latency_class=LatencyClass.MEDIUM,
            multimodal=False,
            privacy_required=privacy,
            task_type=TaskType.CHAT,
        )

    def _is_task_action_request(self, text: str) -> bool:
        """Détermine si la demande utilisateur requiert le lancement d'une mission de worker en arrière-plan."""
        p = text.lower().strip()
        
        # Exceptions : demandes purement conversationnelles ou questions d'état
        if self._is_status_query(p) or self._is_cancel_query(p):
            return False
            
        action_triggers = [
            "analyse g:", "analyse mon disque", "analyse ce", "analyse les", "analyse mon environnement", "analyse l'environnement", "analyse le système", "analyse mon pc",
            "nettoie", "trouve ce qui consomme", "purge le cache", "détecte les caches", "détecter les caches",
            "refais", "implémente", "corrige le bug", "modifie le code", "vibe code",
            "crée ce fichier", "copie ce fichier", "renomme ce fichier", "supprime ce fichier",
            "fais-moi une image", "génère une image", "crée une image",
            "fais-moi un pdf", "génère un rapport", "génère le document",
            "lance une analyse", "améliore ton", "améliore-toi", "améliore le", "ajoute cet outil",
            "lance les tests", "lance le test", "exécute pytest", "execute pytest", "vérifie la non-régression",
            "audit de sécurité", "audit ledger", "scan de secrets", "vérifie les secrets",
            "scrappe", "extrais la page web", "visite le site",
            "transforme le csv", "convertis les données json", "analyse les données",
            "qualifie les modèles", "benchmark le modèle", "teste la latence des providers",
            "automatise ce", "lance ce script", "exécute le script"
        ]
        return any(trig in p for trig in action_triggers)

    def _is_status_query(self, text: str) -> bool:
        """Détecte les questions sur l'état des tâches."""
        p = text.lower().strip()
        status_triggers = [
            "où en est", "ou en est", "quelles tâches", "quelles taches",
            "tâches actives", "taches actives", "état des tâches", "etat des taches",
            "statut de", "status de", "qu'est-ce qui tourne", "montre-moi le dernier résultat"
        ]
        return any(trig in p for trig in status_triggers)

    def _is_cancel_query(self, text: str) -> bool:
        """Détecte les commandes d'annulation de tâche."""
        p = text.lower().strip()
        return any(trig in p for trig in ["annule la tâche", "annule la tache", "arrête la tâche", "arrete la tache", "cancel mission", "cancel task"])

    def _is_pause_query(self, text: str) -> bool:
        """Détecte les demandes de pause/reprise (support backend : voir handler)."""
        p = text.lower().strip()
        return any(trig in p for trig in ["mets en pause", "met en pause", "pause la tâche",
                                          "pause la tache", "suspends la tâche", "reprends la tâche",
                                          "reprends la tache", "resume task"])

    async def _handle_pause_query(self, prompt: str, channel: str) -> Dict[str, Any]:
        """Réponse honnête : les backends workers actuels ne supportent pas
        pause/resume (pas d'état simulé). Annulation coopérative disponible."""
        start_time = time.perf_counter()
        msg = ("Pause non supportée par les backends workers actuels : `NOT_SUPPORTED`. "
               "Aucun état simulé. Options : attendre la fin, demander l'état, "
               "ou annuler (annulation coopérative vérifiée).")
        return {
            "response": msg,
            "answer": msg,
            "content": msg,
            "message": msg,
            "source": "E-ZZIO Master Governor",
            "authority": "CanonicalIdentity",
            "model": "sovereign-master",
            "provider": "master",
            "mission": "PAUSE_QUERY",
            "channel": channel,
            "elapsed_ms": int((time.perf_counter() - start_time) * 1000),
            "ok": True,
            "used_fallback": False,
        }

    async def _handle_ask_query(self, prompt: str, channel: str,
                                intent: str = "ASK",
                                reasons: Optional[List[str]] = None) -> Dict[str, Any]:
        """Clarification déterministe : jamais de devinette, options
        explicites + contexte tâches actives. Aucun appel LLM."""
        start_time = time.perf_counter()
        active = self.registry.list_active()
        options = []
        if active:
            options.append(f"statut des {len(active)} tâche(s) en cours")
            options.append(f"annuler une tâche (précisez son identifiant, ex. #{active[0].mission_id})")
        options.append("lancer une nouvelle tâche (décrivez l'action)")
        options.append("rechercher une information actuelle")
        options.append("discuter (question ouverte)")
        hint = f" Indices détectés : {', '.join((reasons or [])[:2])}." if reasons else ""
        msg = ("Je veux agir avec précision et ne pas deviner. Vouliez-vous : "
               + " / ".join(f"({i+1}) {o}" for i, o in enumerate(options))
               + f" ?{hint} Reformulez ou choisissez un numéro.")
        return {
            "response": msg,
            "answer": msg,
            "content": msg,
            "message": msg,
            "source": "E-ZZIO Master Governor",
            "authority": "CanonicalIdentity",
            "model": "sovereign-master",
            "provider": "master",
            "mission": "ASK_QUERY",
            "channel": channel,
            "elapsed_ms": int((time.perf_counter() - start_time) * 1000),
            "ok": True,
            "used_fallback": False,
            "ask_intent": intent,
        }

    async def _handle_status_query(self, prompt: str, channel: str) -> Dict[str, Any]:
        """Répond immédiatement avec l'état réel des missions actives ou ciblées."""
        start_time = time.perf_counter()
        
        # Vérifier si une mission spécifique est demandée (ex: "où en est A1 ?" ou "où en est la tâche 8F2A ?")
        # Résolution d'ID ancrée (F7) : token court seulement après
        # marqueur explicite (mission|tâche|#), sinon 4+ caractères.
        # Jamais de mot courant ("en", "le") promu en identifiant.
        id_match = re.search(
            r"(?:mission|tâche|tache)\s*#?([A-Za-z0-9_]{2,12})"
            r"|#([A-Za-z0-9_]{2,12})"
            r"|\b([A-Za-z0-9_]{4,12})\b", prompt, re.IGNORECASE)
        target_id = None
        if id_match:
            cand = next((g for g in id_match.groups() if g), "").upper()
            if cand and cand not in ("LA", "UNE", "MON", "TON", "DE"):
                target_id = cand

        active = self.registry.list_active()
        all_missions = self.registry.list_missions(limit=10)

        record = None
        if target_id:
            # Chercher par préfixe ou exact
            for m in all_missions:
                if m.mission_id.upper() == target_id or m.mission_id.upper().endswith(target_id) or target_id in m.mission_id.upper():
                    record = m
                    break

        answered = False
        if not record and active:
            # Sans cible : TOUTES les actives (F6), jamais une seule silencieuse.
            lines = []
            for m in active:
                prog = f"{m.progress} %" if m.progress > 0 else "NON DISPONIBLE"
                lines.append(f"`#{m.mission_id}` [{m.worker_type}] "
                             f"`{m.status.value}` — {m.current_step} "
                             f"(progression : {prog})")
            msg = ("**E-ZZIO**\n\nTâches actives "
                   f"({len(active)}) :\n" + "\n".join(lines))
            answered = True
        elif not record and all_missions:
            # Sans active : état explicite + dernière mission connue en
            # contexte (jamais présentée comme active).
            last = all_missions[0]
            msg = ("Aucune mission active en cours d'exécution. "
                   f"Dernière mission connue : `#{last.mission_id}` "
                   f"(`{last.status.value}`). "
                   "Le Master est disponible pour toute nouvelle instruction.")
            msg += (" Si vous cherchiez une information externe (et non l'état des tâches), "
                    "reformulez en question factuelle (ex. « Quelle est... ? »).")
            answered = True

        if answered:
            pass
        elif record:
            prog_str = f"{record.progress} %" if record.progress > 0 else "NON DISPONIBLE"
            msg = (
                f"**E-ZZIO**\n\n"
                f"Mission : `#{record.mission_id}`\n"
                f"Worker  : `{record.worker_type}`\n"
                f"Status  : `{record.status.value}`\n"
                f"Progression : {prog_str}\n"
                f"Étape   : {record.current_step}\n"
            )
            if record.result and record.result.get("summary"):
                msg += f"\n**Résultat** : {record.result['summary']}"
            if record.artifacts:
                msg += f"\n**Rapports/Artefacts** : {', '.join(record.artifacts)}"
        else:
            msg = "Aucune mission active en cours d'exécution. Le Master est disponible pour toute nouvelle instruction."
            msg += (" Si vous cherchiez une information externe (et non l'état des tâches), "
                    "reformulez en question factuelle (ex. « Quelle est... ? »).")

        return {
            "response": msg,
            "answer": msg,
            "content": msg,
            "message": msg,
            "source": "E-ZZIO Master Governor",
            "authority": "CanonicalIdentity",
            "model": "sovereign-master",
            "provider": "master",
            "mission": "STATUS_QUERY",
            "channel": channel,
            "elapsed_ms": int((time.perf_counter() - start_time) * 1000),
            "ok": True,
            "used_fallback": False,
        }

    async def _handle_cancel_query(self, prompt: str, channel: str) -> Dict[str, Any]:
        """Gère l'annulation sécurisée et non violente d'une mission."""
        start_time = time.perf_counter()
        
        # Trouver un identifiant éventuel
        words = prompt.replace('#', ' ').split()
        target_id = None
        for w in reversed(words):
            w_clean = re.sub(r'[^A-Za-z0-9_]', '', w).upper()
            if len(w_clean) >= 2 and w_clean not in ("LA", "TACHE", "TÂCHE", "MISSION", "ANNULE", "ARRÊTE", "ARRETE", "STOP", "CANCEL"):
                target_id = w_clean
                break

        active = self.registry.list_active()
        all_missions = self.registry.list_missions(limit=50)
        cancelled_id = None
        cancelled_ids: List[str] = []

        # Portée explicite "tout" (F3) : annuler l'ensemble, jamais une seule.
        scope_all = bool(re.search(r"\b(tout|toute|toutes|tous)\b",
                                   (prompt or "").lower()))

        if target_id:
            for m in all_missions:
                if m.mission_id.upper() == target_id or target_id in m.mission_id.upper():
                    if m.status in (MissionStatus.CANCELLED, MissionStatus.COMPLETED,
                                    MissionStatus.FAILED):
                        msg = (f"La mission `#{m.mission_id}` est déjà terminée "
                               f"(`{m.status.value}`) — aucune action.")
                        return {
                            "response": msg, "answer": msg, "content": msg,
                            "message": msg, "source": "E-ZZIO Master Governor",
                            "authority": "CanonicalIdentity", "model": "sovereign-master",
                            "provider": "master", "mission": "CANCEL",
                            "cancel_outcome": "ALREADY_TERMINAL",
                            "channel": channel, "elapsed_ms": int((time.perf_counter() - start_time) * 1000),
                            "ok": True, "used_fallback": False,
                        }
                    if self.registry.cancel(m.mission_id):
                        cancelled_id = m.mission_id
                        break
        if cancelled_id is None and scope_all and active:
            for m in active:
                if self.registry.cancel(m.mission_id):
                    cancelled_ids.append(m.mission_id)
        if cancelled_id is None and not target_id and active:
            if len(active) > 1:
                # Cible ambiguë (F2) : jamais d'annulation arbitraire.
                ids = ", ".join(f"`#{m.mission_id}`" for m in active)
                msg = (f"Plusieurs tâches sont actives ({ids}). "
                       f"Précisez l'identifiant à annuler (ex. #{active[0].mission_id}), "
                       f"ou dites « annule tout » pour tout arrêter.")
                return {
                    "response": msg, "answer": msg, "content": msg,
                    "message": msg, "source": "E-ZZIO Master Governor",
                    "authority": "CanonicalIdentity", "model": "sovereign-master",
                    "provider": "master", "mission": "CANCEL",
                    "cancel_outcome": "DISAMBIGUATE",
                    "channel": channel, "elapsed_ms": int((time.perf_counter() - start_time) * 1000),
                    "ok": True, "used_fallback": False,
                }
            if self.registry.cancel(active[0].mission_id):
                cancelled_id = active[0].mission_id

        if cancelled_ids:
            msg = (f"{len(cancelled_ids)} mission(s) arrêtée(s) : "
                   + ", ".join(f"`#{i}`" for i in cancelled_ids)
                   + ". Le Master reste disponible.")
        elif cancelled_id:
            state = self.registry.get(cancelled_id).status.value
            if state == "CANCELLING":
                msg = f"Annulation demandée pour `#{cancelled_id}`. Statut : `CANCELLING` — je vérifie l'arrêt réel avant de confirmer."
            else:
                msg = f"La mission `#{cancelled_id}` a été arrêtée en toute sécurité. Statut: `CANCELLED`. Le Master reste disponible."
        else:
            msg = f"Impossible de localiser la mission demandée ou aucune tâche active à annuler."

        _cancel_outcome = ("EXECUTED_ALL" if cancelled_ids
                           else "EXECUTED" if cancelled_id else "NO_TARGET")
        return {
            "response": msg,
            "answer": msg,
            "content": msg,
            "message": msg,
            "source": "E-ZZIO Master Governor",
            "authority": "CanonicalIdentity",
            "model": "sovereign-master",
            "provider": "master",
            "mission": "CANCEL",
            "cancel_outcome": _cancel_outcome,
            "channel": channel,
            "elapsed_ms": int((time.perf_counter() - start_time) * 1000),
            "ok": True,
            "used_fallback": False,
        }

    async def _record_assistant_memory(self, res_dict: Dict[str, Any], session_id: str, channel: str) -> Dict[str, Any]:
        if session_id and res_dict.get("response"):
            try:
                if not self._memory_initialized:
                    await self.memory.init()
                    self._memory_initialized = True
                _meta = {
                        "channel": channel,
                        "model": res_dict.get("model"),
                        "provider": res_dict.get("provider"),
                        "mission": res_dict.get("mission")
                    }
                # Observabilité Wave 6 : verdict Truth persisté avec la réponse.
                if res_dict.get("truth_gate"):
                    _meta["truth_gate"] = res_dict.get("truth_gate")
                if res_dict.get("routing_decision", {}).get("action"):
                    _meta["routing_action"] = res_dict["routing_decision"]["action"]
                await self.memory.record_message(
                    session_id=session_id,
                    role="assistant",
                    content=res_dict["response"],
                    metadata=_meta
                )
            except Exception as exc:
                logger.warning("[EzzioMaster] Memory record assistant response failed: %s", exc)
        return res_dict

    async def _build_chat_system_prompt(self, session_id: str = "") -> Optional[str]:
        """Identité canonique + 3 derniers échanges (voie CHAT hermes3:8b)."""
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
        """
        Exécute la requête utilisateur avec séparation nette Master Conversationnel / Workers Asynchrones.
        Le Master ne bloque JAMAIS sur une tâche de worker.
        """
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

        # 1-3. Dispatch gouverné : classification unique (interaction_control)
        # + confirmations étroites (contrats des handlers) + Best Next Action.
        # Le classifieur route, les matchers étroits confirment, BNA arbitre
        # et audite. Parité legacy : délégation confirmée par le narrow set
        # inchangé ; ambiguïté → ASK (jamais de devinette).
        from core.agent.interaction_control import (
            InterruptionIntent, classify_interruption, control_for,
            has_task_reference)
        from core.capabilities.truth_engine import requires_gate as _needs_gate
        from core.capabilities.workspace_decisions import (
            DecisionState, NextAction, best_next_action)
        from core.research_router import HIGH_RISK_KEYWORDS

        _intent, _ireasons = classify_interruption(user_prompt or "")
        _effect = control_for(_intent).task_effect
        # ASK véritable = marqueurs en conflit ou cible destructive floue ;
        # "aucun marqueur" = dialogue normal (parité legacy), pas un doute.
        _needs_clarify = (
            _intent == InterruptionIntent.CLARIFICATION
            or _effect == "MODIFY"
            or (_intent == InterruptionIntent.ASK
                and any(r not in ("aucun marqueur", "texte vide")
                        for r in _ireasons)))
        _gate_needed, _ = _needs_gate(user_prompt or "")
        _risk = any(k in (user_prompt or "").lower()
                    for k in HIGH_RISK_KEYWORDS)
        _destructive = _effect in ("QUERY", "CANCELLING", "PAUSING",
                                   "RESUMING", "MODIFY")
        _delegable = (self._is_task_action_request(user_prompt)
                      and not _destructive)
        _state = DecisionState(
            # has_answer = capacité de réponse conversationnelle (LLM),
            # fausse uniquement en ambiguïté réelle (ASK doit gagner).
            has_answer=(not _needs_clarify),
            ambiguous=_needs_clarify,
            needs_external_info=_gate_needed,
            needs_observation=False,
            needs_specialist=_delegable,
            cancel_requested=(_effect == "CANCELLING"),
            blocked_on_policy=False,
            risk_high=_risk)
        _bna, _bna_why = best_next_action(_state)
        # Frontière honnête (§75) : BNA arbitre la voie informationnelle
        # (ANSWER/SEARCH/DELEGATE/ASK) ; les commandes de cycle de vie
        # (STATUS/CANCEL/PAUSE) sont un fast-path classifieur direct,
        # fail-closed, jamais soumis à l'arbitrage. Le champ bna le trace.
        routing_base = {"reason": _bna_why,
                        "intent": _intent.value, "effect": _effect}
        _BNA_ARBITRATED = ("SEARCH", "ANSWER", "ANSWER_FALLBACK",
                           "DELEGATE", "REJECT", "FAIL_CLOSED")

        def _tag(res, executed):
            bna = _bna.value if executed in _BNA_ARBITRATED else "COMMAND"
            res.setdefault("routing_decision",
                           {**routing_base, "bna": bna, "action": executed})
            return res

        # 1. Statut : effet QUERY + ancrage tâche OU question non factuelle.
        # Garde anti-hijack (F1) : "statut du projet de loi" (factuel, sans
        # référence tâche) tombe vers la recherche au lieu du handler statut.
        _taskish = has_task_reference(user_prompt or "")
        if _effect == "QUERY" and (_taskish or not _gate_needed):
            res = await self._handle_status_query(user_prompt, channel)
            _n_active = len(self.registry.list_active())
            _audit_command("STATUS_QUERY",
                           {"intent": _intent.value, "bna": _bna.value,
                            "active": _n_active,
                            "outcome": "REPORTED" if res.get("ok") else "FAILED"},
                           "SUCCESS" if res.get("ok") else "FAILED")
            return await self._record_assistant_memory(_tag(res, "STATUS"), session_id, channel)

        # 2. Annulation : effet CANCELLING ou contrat étroit historique.
        if _effect == "CANCELLING" or self._is_cancel_query(user_prompt):
            res = await self._handle_cancel_query(user_prompt, channel)
            _audit_command("CANCEL_REQUEST",
                           {"intent": _intent.value, "bna": _bna.value,
                            "mission": res.get("mission", "CANCEL"),
                            "outcome": res.get("cancel_outcome", "UNKNOWN"),
                            "response_head": str(res.get("response", ""))[:160]},
                           "SUCCESS" if res.get("ok") else "FAILED")
            return await self._record_assistant_memory(_tag(res, "CANCEL"), session_id, channel)

        # 2b. Pause/reprise : effet PAUSING/RESUMING ou contrat étroit.
        if _effect in ("PAUSING", "RESUMING") or self._is_pause_query(user_prompt):
            res = await self._handle_pause_query(user_prompt, channel)
            _audit_command("PAUSE_QUERY",
                           {"intent": _intent.value, "bna": _bna.value,
                            "effect": _effect},
                           "SUCCESS" if res.get("ok") else "FAILED")
            return await self._record_assistant_memory(_tag(res, "PAUSE"), session_id, channel)

        # 2c. Ambiguïté réelle ou modification sans contrat → ASK déterministe.
        if _needs_clarify:
            res = await self._handle_ask_query(user_prompt, channel,
                                               _intent.value, _ireasons)
            _audit_command("ASK_CLARIFY",
                           {"intent": _intent.value,
                            "reasons": list(_ireasons[:3])})
            return await self._record_assistant_memory(_tag(res, "ASK"), session_id, channel)

        # 3. Mission d'action confirmée (surface de délégation inchangée).
        if _delegable:
            worker_type = self.fleet.select_worker_for_intent(user_prompt)
            short_id = uuid.uuid4().hex[:4].upper()
            mission_id = f"mission_{short_id}"

            agent_desc = self.agent_registry.get_agent_by_role(worker_type)
            if agent_desc is None:
                # §36 : worker inconnu → REJET, jamais de fallback silencieux
                # transformant l'inconnu en autorisé.
                elapsed_ms = int((time.perf_counter() - start_time) * 1000)
                msg = (f"Worker inconnu du registre : `{worker_type}`. "
                       f"Délégation refusée (fail-closed).")
                res_unknown = {
                    "response": msg, "answer": msg, "content": msg,
                    "message": msg, "source": "E-ZZIO Master Governor",
                    "authority": "CanonicalIdentity", "model": "none",
                    "provider": "none", "mission": "CONTRACT_REJECT",
                    "channel": channel, "elapsed_ms": elapsed_ms,
                    "ok": False, "used_fallback": False,
                }
                _audit_command("UNKNOWN_WORKER_REJECT",
                               {"worker_type": worker_type}, "BLOCKED")
                return await self._record_assistant_memory(
                    _tag(res_unknown, "REJECT"), session_id, channel)
            assigned_agent_id = agent_desc.agent_id if agent_desc else "coder_worker"
            assigned_model = agent_desc.model if agent_desc else "qwen2.5-coder:7b-instruct-q4_K_M"
            assigned_provider = agent_desc.provider if agent_desc else "ollama"

            # 3b. Contrat hiérarchique L0→L1 (fail-closed : rejet si invalide).
            from core.agent.worker_contract import (
                Budget, ContractViolationError, WorkerTaskRequest)
            _contract_error = None
            _req = None
            try:
                _models = {d.model for d in self.agent_registry.list_agents()
                           if getattr(d, "model", None)}
                _models.add(assigned_model)
                _req = WorkerTaskRequest(
                    request_id=str(uuid.uuid4()),
                    task_id=mission_id, parent_task_id=None,
                    worker_id=assigned_agent_id, worker_type=worker_type,
                    objective=user_prompt,
                    authorized_tools=tuple(
                        _WORKER_TOOL_AUTH.get(worker_type, ())),
                    authorized_models=(assigned_model,),
                    budget=Budget(timeout_sec=900, max_retries=0,
                                  max_children=0, max_tool_calls=50,
                                  max_llm_calls=5, max_search_calls=5),
                    priority="P2",
                    context={"goal": user_prompt[:2000]},
                    truth_requirements={"untrusted_result": True},
                    depth=1, max_children=0,
                    memory_scope="task", memory_ids=(),
                    memory_budget=4)
                _req.ensure_valid()
                _auth_errors = _req.authorize_against(
                    tuple(self.fleet.WORKER_MAPPING.keys()),
                    _KNOWN_TOOL_NAMES, tuple(sorted(_models)))
                if _auth_errors:
                    raise ContractViolationError("; ".join(_auth_errors))
            except ContractViolationError as _cexc:
                _contract_error = str(_cexc)
            if _contract_error:
                elapsed_ms = int((time.perf_counter() - start_time) * 1000)
                msg = (f"Mission refusée par le contrat L0→L1 : "
                       f"{_contract_error}")
                res_contract_reject = {
                    "response": msg, "answer": msg, "content": msg,
                    "message": msg, "source": "E-ZZIO Master Governor",
                    "authority": "CanonicalIdentity", "model": "none",
                    "provider": "none", "mission": "CONTRACT_REJECT",
                    "channel": channel, "elapsed_ms": elapsed_ms,
                    "ok": False, "used_fallback": False,
                }
                return await self._record_assistant_memory(
                    _tag(res_contract_reject, "REJECT"), session_id, channel)

            record = MissionRecord(
                mission_id=mission_id,
                request_id=_req.request_id,
                contract={"schema": _req.schema_version,
                          "request_id": _req.request_id,
                          "worker_id": _req.worker_id,
                          "worker_type": _req.worker_type,
                          "budget": {"timeout_sec": _req.budget.timeout_sec,
                                     "max_retries": _req.budget.max_retries,
                                     "max_children": _req.budget.max_children,
                                     "max_tool_calls":
                                         _req.budget.max_tool_calls},
                          "authorized_tools": list(_req.authorized_tools),
                          "authorized_models": list(_req.authorized_models),
                          "priority": _req.priority, "depth": _req.depth,
                          "memory_scope": _req.memory_scope,
                          "memory_ids": list(_req.memory_ids),
                          "memory_budget": _req.memory_budget},
                goal=user_prompt,
                worker_type=worker_type,
                model=assigned_model,
                provider=assigned_provider,
                status=MissionStatus.RUNNING,
                progress=10,
                current_step="Initialisation du worker",
                channel=channel,
                session_id=session_id,
                user_id=user_id,
            )
            self.registry.register(record)


            # Lancement asynchrone non-bloquant en tâche de fond
            async_task = asyncio.create_task(self.fleet.execute_mission_async(record))
            record.async_task = async_task

            elapsed_ms = int((time.perf_counter() - start_time) * 1000)
            ack_message = (
                f"E-ZZIO\n\n"
                f"Je délègue la mission au `{worker_type}` ({assigned_agent_id}).\n\n"
                f"Mission :\n`#{mission_id}` ({record.worker_type})\n\n"
                f"Status :\nRUNNING\n\n"
                f"Je reste disponible pour continuer à échanger."
            )

            res_ack = {
                "response": ack_message,
                "answer": ack_message,
                "content": ack_message,
                "message": ack_message,
                "source": f"Master Dispatcher -> {worker_type}",
                "authority": "CanonicalIdentity",
                "model": record.model,
                "provider": record.provider,
                "mission": mission_id,
                "worker": worker_type,
                "agent_id": assigned_agent_id,
                "channel": channel,
                "elapsed_ms": elapsed_ms,
                "ok": True,
                "used_fallback": False,
                "is_async_job": True,
            }
            return await self._record_assistant_memory(_tag(res_ack, "DELEGATE"), session_id, channel)

        # 4. Requête conversationnelle normale (Explications, architecture, questions générales)
        try:
            profile = self._resolve_task_profile(
                mission_profile=mission_profile,
                model_target=model_target,
                speed=speed,
                force_cloud=force_cloud,
            )
        except UnknownModelTargetError as exc:
            elapsed_ms = int((time.perf_counter() - start_time) * 1000)
            logger.error("[EzzioMaster] Target modèle rejeté : %s", exc)
            try:
                self.federation_router._record_audit(
                    action="MASTER_TARGET_REJECTED",
                    payload={"model_target": model_target, "reason": str(exc)},
                    status="REJECTED",
                )
            except Exception as audit_exc:
                logger.warning("[EzzioMaster] Audit rejet target impossible : %s", audit_exc)
            res_reject = {
                "response": str(exc),
                "answer": str(exc),
                "content": str(exc),
                "message": str(exc),
                "source": "Master Target Validation",
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
            return await self._record_assistant_memory(_tag(res_reject, "REJECT"), session_id, channel)

        # 4b. Chemin recherche live : question factuelle → internal-first
        # (contexte session ; mémoire gateway non câblée au master par
        # conception → DEFERRED P2 documenté) → plan → multi-source →
        # claims → truth gate → réponse déterministe. Échec ou 0 preuve →
        # repli fédération + mention UNVERIFIED (comportement antérieur).
        from core.capabilities.truth_engine import requires_gate as _needs_gate
        if _needs_gate(user_prompt or "")[0]:
            try:
                from core.research_router import run_adaptive_research
                from core.capabilities.truth_engine import (
                    apply_output_gate as _rgate)
                _research = await asyncio.wait_for(
                    run_adaptive_research(user_prompt or ""), timeout=40.0)
                if _research.get("answer") and _research.get("status") in (
                        "COMPLETE", "PARTIAL"):
                    _rv, _rn = _rgate(user_prompt or "",
                                      _research.get("claims") or None)
                    _answer = _research["answer"] + (("\n\n" + _rn) if _rn else "")
                    res_research = {
                        "response": _answer,
                        "answer": _answer,
                        "content": _answer,
                        "message": _answer,
                        "source": ("live-research ("
                                   + ",".join(s["source"] for s in
                                              _research.get("sources", [])) + ")"),
                        "authority": "CanonicalIdentity",
                        "model": "none",
                        "provider": "research-fabric",
                        "mission": mission_profile or "STANDARD",
                        "channel": channel,
                        "elapsed_ms": int((time.perf_counter() - start_time) * 1000),
                        "ok": True,
                        "used_fallback": False,
                        "truth_gate": _rv,
                        "research": {
                            "status": _research.get("status"),
                            "intent": _research.get("intent"),
                            "breadth": _research.get("breadth"),
                            "independent_origins": _research.get("independent_origins"),
                            "claims_count": len(_research.get("claims", []) or []),
                            "rounds": _research.get("rounds", []),
                            "confidence": _research.get("confidence"),
                            "quality": _research.get("quality"),
                            "gate_verdict": _research.get("gate_verdict"),
                            "latency_ms": _research.get("latency_ms"),
                            "mode": _research.get("mode"),
                            "stop_reason": _research.get("stop_reason"),
                            "provider_calls": _research.get("provider_calls"),
                        },
                    }
                    import hashlib as _hl
                    _audit_command("RESEARCH_OUTCOME", {
                        "query_hash": _hl.sha256(
                            (user_prompt or "").encode("utf-8")).hexdigest()[:16],
                        "claims": len(_research.get("claims", []) or []),
                        "origins": _research.get("independent_origins"),
                        "rounds": [{"source": _r.get("source"),
                                    "status": _r.get("status"),
                                    "n_claims": _r.get("n_claims"),
                                    "n_origins": _r.get("n_origins")}
                                   for _r in (_research.get("rounds", []) or [])],
                        "stop_reason": _research.get("stop_reason"),
                        "mode": _research.get("mode"),
                        "provider_calls": _research.get("provider_calls"),
                        "gate_verdict": str(_research.get("gate_verdict")),
                        "session_id": session_id or ""})
                    return await self._record_assistant_memory(
                        _tag(res_research, "SEARCH"), session_id, channel)
            except Exception as _rexc:
                logger.warning(
                    "[EzzioMaster] Recherche live impossible, repli fédération : %s",
                    _rexc)

        try:
            # 4-MULTI. Débat multi-agents opt-in (EZZIO_MULTI_AGENT=1, >STANDARD).
            # Désactivé par défaut : aucun changement de comportement sinon.
            try:
                from core.agents.multi_agent_flow import MultiAgentFlow, should_auto_trigger
                if should_auto_trigger(profile, mission_profile):
                    mres = await MultiAgentFlow().run(user_prompt)
                    elapsed_ms = int((time.perf_counter() - start_time) * 1000)
                    res_multi = {
                        "response": mres["consensus"], "answer": mres["consensus"],
                        "content": mres["consensus"], "message": mres["consensus"],
                        "source": "MultiAgentFlow", "authority": "CanonicalIdentity",
                        "model": "multi-agent", "provider": "federation",
                        "mission": mission_profile or "STANDARD",
                        "channel": channel, "elapsed_ms": elapsed_ms,
                        "ok": True, "used_fallback": False,
                        "multi_agent": {"domains": mres["domains"],
                                        "adrs": [a["adr_id"] for a in mres["adrs"]]},
                    }
                    _audit_command("MULTI_AGENT", {
                        "domains": mres["domains"],
                        "adrs": [a["adr_id"] for a in mres["adrs"]]})
                    return await self._record_assistant_memory(
                        _tag(res_multi, "ANSWER"), session_id, channel)
            except Exception as mexc:
                logger.warning("[EzzioMaster] Multi-agent ignoré, voie normale : %s", mexc)

            # 4-MEM. Mémoire→L0 (§4-8) : retrieval ciblé, jamais total ;
            # contenu WRAPPÉ UNTRUSTED (DATA, jamais instruction/commande).
            _effective_prompt = user_prompt
            try:
                from core.memory.tiers import memory_need, retrieve
                from core.security.untrusted import wrap_untrusted
                _need, _tiers = memory_need(
                    user_prompt or "",
                    has_active_tasks=bool(self.registry.list_active()))
                if _need != "NO_MEMORY":
                    if not self._memory_initialized:
                        await self.memory.init()
                        self._memory_initialized = True
                    _mem = await retrieve(
                        self.memory, query=user_prompt or "",
                        task_id="", project_id=(session_id or "default"),
                        tiers=_tiers if _tiers else ["working"],
                        max_memories=2, max_chars=1500)
                    _cells = _mem.get("memories", [])
                    if _cells:
                        _lines = "\n".join(
                            f"- [{c['tier']}/{c['scope']} "
                            f"état={c['truth_state']}] {c['content'][:400]}"
                            for c in _cells)
                        _block = (
                            "Contexte mémorisé (NON AUTORITAIRE : états de "
                            "vérité inclus, ne jamais présenter comme fait "
                            "vérifié sans preuve actuelle) :\n" + _lines)
                        _effective_prompt = (
                            wrap_untrusted(_block, source="memory") + "\n\n"
                            + (user_prompt or ""))
                        _audit_command("MEMORY_USED", {
                            "need": _need, "tiers": _tiers,
                            "memories": len(_cells),
                            "memory_ids": [c["memory_id"] for c in _cells],
                            "session_id": session_id or ""})
            except Exception as _mexc:
                logger.warning("[EzzioMaster] Retrieval mémoire ignoré : %s",
                               _mexc)
            # Identité canonique + contexte injectés en system (toute voie
            # conversationnelle : le system explicite reste prioritaire).
            chat_system = system_prompt or await self._build_chat_system_prompt(session_id)
            fed_resp: ProviderResponse = await self.federation_router.execute_task(
                prompt=_effective_prompt,
                profile=profile,
                system_prompt=chat_system if chat_system else None,
            )
            elapsed_ms = int((time.perf_counter() - start_time) * 1000)

            reply = fed_resp.content or ""
            model_name = fed_resp.model or "unknown-model"
            provider_name = fed_resp.provider or "unknown-provider"
            raw_trace = fed_resp.raw.get("coder_federation_trace", {}) if isinstance(fed_resp.raw, dict) else {}
            used_fallback = bool(raw_trace.get("attempts_count", 0) > 1) if raw_trace else False

            if not reply.strip():
                # Fail-closed strict (F1) : réponse fédérée vide = refus audité,
                # aucun appel de secours hors gouvernance.
                _audit_command("FEDERATION_EMPTY", {
                    "mission": mission_profile or "STANDARD",
                    "provider": provider_name, "model": model_name,
                    "outcome": "REFUSED"}, "BLOCKED")
                raise GovernanceError(
                    "[FAIL-CLOSED] Fédération sans réponse exécutable : exécution refusée, aucun secours.")

            status_ok = bool(reply.strip())

            # TRUTH GATE (dernier contrôle avant publication) : toute réponse
            # issue du LLM sans claims structurés et portant sur un fait
            # externe vérifiable reçoit la mention UNVERIFIED (fail-closed).
            # Voies status/tâche = mesures système propres → exemptées.
            from core.capabilities.truth_engine import apply_output_gate
            truth_verdict, truth_notice = apply_output_gate(user_prompt or "")
            if truth_notice and status_ok:
                reply = reply + "\n\n" + truth_notice

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
                "ok": status_ok,
                "used_fallback": used_fallback,
                "federation_trace": raw_trace,
                "truth_gate": truth_verdict,
            }
            _audit_command("CONV_MODEL", {
                "model": model_name, "provider": provider_name,
                "used_fallback": used_fallback,
                "mission": mission_profile or "STANDARD",
                "outcome": "RESPONDED" if status_ok else "EMPTY",
                "truth_gate": str(truth_verdict),
                "session_id": session_id or ""})
            return await self._record_assistant_memory(_tag(res_conv, "ANSWER"), session_id, channel)

        except Exception as exc:
            elapsed_ms = int((time.perf_counter() - start_time) * 1000)
            logger.error("[EzzioMaster] Exception during execution: %s", exc)

            _audit_command("FEDERATION_EXCEPTION", {
                "error": str(exc)[:300],
                "mission": mission_profile or "STANDARD",
                "outcome": "REFUSED"}, "BLOCKED")
            fail_msg = f"[FAIL-CLOSED] Liaison Fédération E-ZZIO indisponible : {exc}"
            res_fail = {
                "response": fail_msg,
                "answer": fail_msg,
                "content": fail_msg,
                "message": fail_msg,
                "source": "Federation Fail-Closed",
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
            return await self._record_assistant_memory(_tag(res_fail, "FAIL_CLOSED"), session_id, channel)


ezzio_master = EzzioMaster()
