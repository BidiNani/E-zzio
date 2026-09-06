"""E-ZZIO Master Orchestrator — Mono-Autorité Identitaire, Conversationnel & Workers Asynchrones."""
from __future__ import annotations
import re
import uuid
import time
import asyncio
import logging
from datetime import datetime, timezone
from typing import Any, Dict, Optional, List

from core.cloud_brain_broker import cloud_chat
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
from core.providers.base_provider import ProviderResponse

logger = logging.getLogger("EzzioMaster")


class EzzioMaster:
    """Orchestrateur central E-ZZIO : Master conversationnel immédiat + Workers asynchrones."""

    def __init__(self, federation_router: Optional[CoderModelFederationRouter] = None) -> None:
        self.federation_router = federation_router or coder_federation_router
        self.fleet = worker_fleet
        self.registry = mission_registry
        self.agent_registry = agent_registry

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

        if profile_key in ("COMPLEX", "CRITICAL") or target in ("nvidia", "nvidia_nim"):
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
        privacy = PrivacyRequirement.CLOUD_ALLOWED if force_cloud else PrivacyRequirement.LOCAL_PREFERRED
        return TaskProfile(
            complexity=TaskComplexity.STANDARD,
            context_size=ContextSize.NORMAL,
            latency_class=LatencyClass.MEDIUM,
            multimodal=False,
            privacy_required=privacy,
            task_type=TaskType.CODING,
        )

    def _is_task_action_request(self, text: str) -> bool:
        """Détermine si la demande utilisateur requiert le lancement d'une mission de worker en arrière-plan."""
        p = text.lower().strip()
        
        # Exceptions : demandes purement conversationnelles ou questions d'état
        if self._is_status_query(p) or self._is_cancel_query(p):
            return False
            
        action_triggers = [
            "analyse g:", "analyse mon disque", "analyse ce", "analyse les",
            "nettoie", "trouve ce qui consomme", "purge le cache",
            "refais", "implémente", "corrige le bug", "modifie le code", "vibe code",
            "crée ce fichier", "copie ce fichier", "renomme ce fichier", "supprime ce fichier",
            "fais-moi une image", "génère une image", "crée une image",
            "fais-moi un pdf", "génère un rapport", "génère le document",
            "lance une analyse", "améliore ton", "améliore-toi", "ajoute cet outil",
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

    async def _handle_status_query(self, prompt: str, channel: str) -> Dict[str, Any]:
        """Répond immédiatement avec l'état réel des missions actives ou ciblées."""
        start_time = time.perf_counter()
        
        # Vérifier si une mission spécifique est demandée (ex: "où en est A1 ?" ou "où en est la tâche 8F2A ?")
        id_match = re.search(r'(?:mission|tâche|tache)?\s*#?([A-Za-z0-9_]{2,12})', prompt, re.IGNORECASE)
        target_id = None
        if id_match:
            cand = id_match.group(1).upper()
            if cand not in ("LA", "UNE", "MON", "TON", "DE"):
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

        if not record and active:
            # Si aucune mission spécifiée, prendre la dernière active
            record = active[0]

        if record:
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

        if target_id:
            for m in all_missions:
                if m.mission_id.upper() == target_id or target_id in m.mission_id.upper():
                    if self.registry.cancel(m.mission_id):
                        cancelled_id = m.mission_id
                        break
        elif active:
            if self.registry.cancel(active[0].mission_id):
                cancelled_id = active[0].mission_id

        if cancelled_id:
            msg = f"La mission `#{cancelled_id}` a été arrêtée en toute sécurité. Statut: `CANCELLED`. Le Master reste disponible."
        else:
            msg = f"Impossible de localiser la mission demandée ou aucune tâche active à annuler."

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
            "channel": channel,
            "elapsed_ms": int((time.perf_counter() - start_time) * 1000),
            "ok": True,
            "used_fallback": False,
        }

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

        # 1. Vérifier si c'est une requête de statut
        if self._is_status_query(user_prompt):
            return await self._handle_status_query(user_prompt, channel)

        # 2. Vérifier si c'est une requête d'annulation
        if self._is_cancel_query(user_prompt):
            return await self._handle_cancel_query(user_prompt, channel)

        # 3. Vérifier si c'est une mission d'action pour un Worker Asynchrone
        if self._is_task_action_request(user_prompt):
            worker_type = self.fleet.select_worker_for_intent(user_prompt)
            short_id = uuid.uuid4().hex[:4].upper()
            mission_id = f"mission_{short_id}"

            agent_desc = self.agent_registry.get_agent_by_role(worker_type)
            assigned_agent_id = agent_desc.agent_id if agent_desc else "coder_worker"
            assigned_model = agent_desc.model if agent_desc else "qwen3.5:9b"
            assigned_provider = agent_desc.provider if agent_desc else "ollama"

            record = MissionRecord(
                mission_id=mission_id,
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

            return {
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

        # 4. Requête conversationnelle normale (Explications, architecture, questions générales)
        profile = self._resolve_task_profile(
            mission_profile=mission_profile,
            model_target=model_target,
            speed=speed,
            force_cloud=force_cloud,
        )

        try:
            fed_resp: ProviderResponse = await self.federation_router.execute_task(
                prompt=user_prompt,
                profile=profile,
                system_prompt=system_prompt if system_prompt else None,
            )
            elapsed_ms = int((time.perf_counter() - start_time) * 1000)

            reply = fed_resp.content or ""
            model_name = fed_resp.model or "unknown-model"
            provider_name = fed_resp.provider or "unknown-provider"
            raw_trace = fed_resp.raw.get("coder_federation_trace", {}) if isinstance(fed_resp.raw, dict) else {}
            used_fallback = bool(raw_trace.get("attempts_count", 0) > 1) if raw_trace else False

            if not reply.strip() and profile.privacy_required != PrivacyRequirement.LOCAL_ONLY:
                cloud_res = cloud_chat(text=user_prompt, session_id=session_id, speed=speed)
                elapsed_ms = int((time.perf_counter() - start_time) * 1000)
                reply = cloud_res.get("response") or cloud_res.get("answer") or cloud_res.get("content") or ""
                model_name = cloud_res.get("model", "gemini-2.5-flash")
                provider_name = "gemini"
                used_fallback = True

            status_ok = bool(reply.strip())

            return {
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
            }

        except Exception as exc:
            elapsed_ms = int((time.perf_counter() - start_time) * 1000)
            logger.error("[EzzioMaster] Exception during execution: %s", exc)

            if profile.privacy_required != PrivacyRequirement.LOCAL_ONLY:
                try:
                    cloud_res = cloud_chat(text=user_prompt, session_id=session_id, speed=speed)
                    reply = cloud_res.get("response") or cloud_res.get("answer") or cloud_res.get("content") or ""
                    model_name = cloud_res.get("model", "gemini-2.5-flash")
                    return {
                        "response": reply,
                        "answer": reply,
                        "content": reply,
                        "message": reply,
                        "source": f"gemini ({model_name})",
                        "authority": "CanonicalIdentity",
                        "model": model_name,
                        "provider": "gemini",
                        "mission": mission_profile or "STANDARD",
                        "channel": channel,
                        "elapsed_ms": int((time.perf_counter() - start_time) * 1000),
                        "ok": True,
                        "used_fallback": True,
                    }
                except Exception as cloud_exc:
                    logger.error("[EzzioMaster] Ultimate fallback failed: %s", cloud_exc)

            fail_msg = f"[FAIL-CLOSED] Liaison Fédération E-ZZIO indisponible : {exc}"
            return {
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


ezzio_master = EzzioMaster()
