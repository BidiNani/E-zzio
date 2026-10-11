"""
E-ZZIO Core — Tactical Model Router (ECOL V7.61)
Sélectionne le moteur cognitif en fonction du vecteur de coût et de la capacité requise.
"""

import logging
from typing import Any

from core.cognition.local_autonomy import (
    LocalAutonomyManager,
    LocalEscalationEvent,
)
from core.routing import registry as canonical_registry
from core.routing.model_registry import canonical_model_registry

logger = logging.getLogger(__name__)


class ModelRouter:
    def __init__(self, local_autonomy: LocalAutonomyManager | None = None):
        self.local_autonomy = local_autonomy or LocalAutonomyManager()

    def _resolve_explicit_target(self, model_target: str) -> dict[str, Any] | None:
        """Valide et résout une cible explicite contre la SOURCE CANONIQUE (registry).

        Accepte uniquement une cible RÉELLEMENT connue de la source unique
        `core.routing.registry` :
          - un ID de modèle canonique exact (y compris ceux contenant un '/',
            ex: "groq/llama-3.3-70b", "mistral/mistral-large")
          - un nom de provider seul ("gemini", "groq"...) -> modèle PAR DÉFAUT du provider
          - un nom de modèle local connu ("qwen2.5-coder:7b-instruct-q4_K_M")
          - les jetons "local"/"ollama"
        Toute cible inconnue est FAIL-CLOSED : aucune cible arbitraire hors registre.
        """
        raw = (model_target or "").strip()
        lowered = raw.lower()

        # 1. Jetons canoniques "local"/"ollama"
        if lowered in ("local", "ollama"):
            local_rec = canonical_model_registry.get_by_role("LOCAL") or canonical_model_registry.get_by_role("LOCAL_CODING")
            if local_rec and local_rec.source.name == "LOCAL":
                return {"provider": "ollama", "model": local_rec.name}
            return {"provider": "ollama", "model": canonical_registry.default_local()}

        # 2. ID de modèle canonique EXACT (prioritaire : gère les ids à slashs)
        spec = canonical_registry.get_model(raw)
        if spec is not None:
            return {"provider": spec.provider, "model": spec.id}

        # 3. Nom de provider seul -> modèle par défaut canonique
        if lowered in canonical_registry.PROVIDERS:
            return {"provider": lowered, "model": canonical_registry.PROVIDERS[lowered].default_model}

        # 4. Modèle canonique par rôle (cloud, ex: "gemini-3.5-flash")
        rec = canonical_model_registry.get(raw)
        if rec and getattr(rec, "provider", ""):
            return {"provider": rec.provider, "model": rec.name}

        # 5. Modèle local connu
        if canonical_registry.get_local(raw):
            return {"provider": "ollama", "model": raw}

        # 6. Forme "provider/modèle" avec provider canonique mais id non déclaré -> FAIL-CLOSED
        #    (on n'invente jamais un modèle) ; idem provider inconnu.
        return None

    def select_engine(
        self,
        task_type: str = "general",
        complexity_score: float = 0.5,
        risk_level: str = "low",
        channel: str = "web",
        is_mission: bool = False,
        policy_permits_local: bool = True,
        budget_permits_cloud: bool = True,
        prefer_local: bool = False,
        context_tokens: int = 1000,
        **kwargs
    ) -> dict[str, Any]:
        """Aiguillage capacitaire et conversationnel basé sur le registre canonique et l'autonomie locale."""
        task_lower = (task_type or "").lower()

        # 0. Resolution d'un model_target explicite si fourni (ex: "groq/llama-3.3-70b" ou "gemini-3.5-flash")
        model_target = kwargs.get("model_target")
        if model_target and model_target != "auto":
            local_only = bool(kwargs.get("local_only", False))
            # Gouvernance : la cible explicite est VALIDEE contre la source canonique
            # (core.routing.registry). Toute cible inconnue -> FAIL-CLOSED.
            resolved = self._resolve_explicit_target(model_target)
            if resolved is None:
                return {
                    "status": "FAIL_CLOSED",
                    "error": "UNKNOWN_MODEL_TARGET",
                    "reason": f"model_target '{model_target}' is not a canonical provider/model (registry)",
                    "provider": None,
                    "model": None,
                }
            provider = resolved["provider"]
            model_name = resolved["model"]
            is_local_target = (provider == "ollama")
            # Souverainete (LOCAL-FIRST) : local_only interdit toute cible cloud,
            # y compris explicite. FAIL-CLOSED observable, jamais de bascule cloud implicite.
            if local_only and not is_local_target:
                return {
                    "status": "FAIL_CLOSED",
                    "error": "LOCAL_ONLY_BLOCKS_CLOUD_TARGET",
                    "reason": f"local_only=True forbids cloud target '{model_target}' (resolved provider={provider})",
                    "provider": None,
                    "model": None,
                }
            return {
                "provider": provider,
                "model": model_name,
                "thinking_level": "off",
                "role": "EXPLICIT_TARGET",
                "is_local": is_local_target,
                "local_only": local_only,
            }

        # 1. Évaluation Local-First si demandé ou compatible
        if prefer_local or task_lower == "local" or task_lower.startswith("local_"):
            is_local_eligible, reason = self.local_autonomy.evaluate_local_first(
                task_type=task_type,
                complexity_score=complexity_score,
                context_tokens=context_tokens,
                policy_permits_local=policy_permits_local,
                budget_permits_cloud=budget_permits_cloud,
            )

            if is_local_eligible:
                # Modèle local sélectionné depuis le registre canonique (rôles LOCAL
                # uniquement — les rôles FAST/CODING sont des rôles cloud).
                local_rec = (
                    canonical_model_registry.get_by_role("LOCAL")
                    or canonical_model_registry.get_by_role("LOCAL_CODING")
                    or canonical_model_registry.get_by_role("FAST_LOCAL")
                )
                if local_rec is not None and local_rec.source.name == "LOCAL":
                    local_model = local_rec.name
                else:
                    try:
                        local_model = canonical_registry.default_local()
                    except Exception:
                        return {
                            "status": "FAIL_CLOSED",
                            "error": "NO_LOCAL_ENGINE",
                            "reason": "Local eligible but no canonical local engine declared (registry)",
                            "provider": None,
                            "model": None,
                        }
                logger.info(f"Routage LOCAL autonome sélectionné -> Modèle: {local_model} (Raison: {reason})")
                return {
                    "provider": "ollama",
                    "model": local_model,
                    "thinking_level": "off",
                    "role": "LOCAL_AUTONOMOUS",
                    "is_local": True,
                }
            else:
                # Événement d'escalade observable (Pas de fallback silencieux).
                # Le repli cloud dérive du registre (jamais d'ID déprécié codé en dur).
                fallback_role = "CODING" if ("code" in task_lower or "coding" in task_lower) else "FAST_CHAT"
                fallback_rec = canonical_model_registry.get_by_role(fallback_role)
                if fallback_rec is not None:
                    fallback_model = fallback_rec.name
                    fallback_provider = fallback_rec.provider or "gemini"
                else:
                    fallback_model = canonical_registry.PROVIDERS["gemini"].default_model
                    fallback_provider = "gemini"

                if not budget_permits_cloud:
                    # RÈGLE A11 : Budget bloque cloud -> FAIL-CLOSED
                    return {
                        "status": "FAIL_CLOSED",
                        "error": "BUDGET_BLOCKS_CLOUD",
                        "reason": f"Local unavailable ({reason}) and budget denies cloud escalation",
                        "provider": None,
                        "model": None,
                    }

                try:
                    attempted_model = canonical_registry.default_local()
                except Exception:
                    attempted_model = "unknown-local"
                escalation = LocalEscalationEvent(
                    event_type="LOCAL_UNAVAILABLE",
                    reason=reason,
                    attempted_model=attempted_model,
                    fallback_model=fallback_model,
                    fallback_provider=fallback_provider,
                )
                self.local_autonomy.record_execution(
                    provider=fallback_provider,
                    was_local_intended=True,
                    escalation_event=escalation,
                )

        # 2. Spécification classique par rôles canoniques
        if "code" in task_lower or "coding" in task_lower or "architecture" in task_lower:
            role = "CODING"
            thinking = "low"
        elif "forensic" in task_lower:
            role = "FORENSIC"
            thinking = "medium"
        elif "refactor" in task_lower:
            role = "REFACTOR"
            thinking = "medium"
        elif "infra" in task_lower or "fast_local" in task_lower:
            role = "FAST"
            thinking = "off"
        # Chat / Conversational & Strategic Missions
        elif complexity_score < 0.3 and risk_level == "low":
            role = "FAST_CHAT"
            thinking = "off"
        elif complexity_score < 0.7 and not (is_mission and complexity_score >= 0.7):
            role = "STANDARD_CHAT"
            thinking = "medium" if complexity_score >= 0.5 else "low"
        elif complexity_score >= 0.85:
            role = "MASTER_STRATEGIC"
            thinking = "high"
        else:
            role = "MASTER_STRATEGIC"
            thinking = "medium"

        # Lookup in canonical registry by role
        record = canonical_model_registry.get_by_role(role)

        # Fallback to MASTER if role not registered
        if not record:
            record = canonical_model_registry.get_by_role("MASTER_STRATEGIC") or canonical_model_registry.get_by_role("MASTER")

        # Gouvernance : aucun moteur canonique -> FAIL-CLOSED (jamais de modèle fabriqué).
        if record is None:
            return {
                "status": "FAIL_CLOSED",
                "error": "NO_CANONICAL_ENGINE",
                "reason": f"No canonical engine for role '{role}' (registry)",
                "provider": None,
                "model": None,
            }
        engine = record.name
        if record and getattr(record, "provider", ""):
            provider = record.provider
        elif record and record.source.name == "LOCAL":
            provider = "ollama"
        else:
            provider = "gemini"

        logger.info(
            f"Routage cognitif -> Canal: {channel} | Rôle: {role} | Moteur: {engine} | Thinking: {thinking} | Provider: {provider}"
        )
        return {"provider": provider, "model": engine, "thinking_level": thinking, "role": role, "is_local": provider == "ollama"}
