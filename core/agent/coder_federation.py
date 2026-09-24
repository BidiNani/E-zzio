"""
core/agent/coder_federation.py — Compatibility Gateway & Model Routing Adapter
Re-exports canonical router types for historical test contracts while ensuring zero bypass.
"""
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Any

from core.ezzio_master import ezzio_master
from core.providers.base_provider import CostClass, ProviderResponse


class TaskComplexity(Enum):
    MICRO = auto()
    STANDARD = auto()
    COMPLEX = auto()
    ARCHITECTURAL = auto()


class TaskType(Enum):
    GENERAL = auto()
    CODING = auto()
    REASONING = auto()
    SYSTEM = auto()


class ContextSize(Enum):
    SMALL = auto()
    NORMAL = auto()
    MEDIUM = auto()
    LARGE = auto()


class LatencyClass(Enum):
    ULTRA_FAST = auto()
    FAST = auto()
    BALANCED = auto()
    DEEP = auto()


class PrivacyRequirement(Enum):
    LOCAL_ONLY = auto()
    PREFER_LOCAL = auto()
    ALLOW_CLOUD = auto()


@dataclass
class TaskProfile:
    complexity: TaskComplexity = TaskComplexity.STANDARD
    task_type: TaskType = TaskType.GENERAL
    context_size: ContextSize = ContextSize.MEDIUM
    latency_preference: LatencyClass = LatencyClass.BALANCED
    privacy: PrivacyRequirement = PrivacyRequirement.ALLOW_CLOUD
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class ProviderCandidate:
    provider_name: str
    model_name: str
    cost_class: CostClass = CostClass.CLOUD
    capabilities: list[str] = field(default_factory=list)
    is_local: bool = False


@dataclass
class RoutingPlan:
    primary: ProviderCandidate | None = None
    fallback_chain: list[ProviderCandidate] = field(default_factory=list)

CoderRoutingPlan = RoutingPlan


class RoutingIntegrityError(RuntimeError):
    """Exception raised when routing governance contract fails."""
    pass


def _normalize_model_name(name: str) -> str:
    if not name:
        return "gemini-3.5-flash-lite"
    n = name.lower().strip()
    if "gemini" in n:
        return "gemini-3.5-flash-lite"
    if "qwen" in n or "ollama" in n:
        return "qwen2.5-coder:7b"
    return name


# Fallback hardcoded (utilise si le registre canonique est indisponible)
_DEFAULT_MODELS_FALLBACK: dict[str, str] = {
    "gemini": "gemini-3.5-flash-lite",
    "ollama": "qwen2.5-coder:7b",
    "groq": "llama-3.3-70b-versatile",
}


def _build_default_models() -> dict[str, str]:
    """Dérive le mapping provider -> modèle par défaut depuis la sémantique du CanonicalModelRegistry.

    Phase 2.3A Étape 3A : sémantique basée sur les rôles du registre.
    Ne boucle plus en écrasant 'le dernier modèle rencontré'.
    Fallback de compatibilité si le registre est indisponible.
    """
    try:
        from core.routing.model_registry import canonical_model_registry
        result = dict(_DEFAULT_MODELS_FALLBACK)

        gemini_rec = canonical_model_registry.get_by_role("STANDARD_CHAT") or canonical_model_registry.get_by_role("FAST_CHAT")
        if gemini_rec and gemini_rec.name:
            result["gemini"] = gemini_rec.name

        ollama_rec = canonical_model_registry.get_by_role("LOCAL_CODING") or canonical_model_registry.get_by_role("LOCAL")
        if ollama_rec and ollama_rec.name:
            result["ollama"] = ollama_rec.name

        groq_recs = [m for m in canonical_model_registry.list_models() if m.provider == "groq"]
        if groq_recs:
            result["groq"] = groq_recs[0].name

        return result
    except Exception:
        return dict(_DEFAULT_MODELS_FALLBACK)


class CoderModelFederationRouter:
    """Passerelle de fédération canonique déléguant vers EzzioMaster."""

    DEFAULT_MODELS = _build_default_models()

    def __init__(
        self,
        providers: dict[str, Any] | None = None,
        cb: Any = None,
        audit_ledger: Any = None,
        max_cloud_budget_cents: int = 1000,
    ):
        self.providers = providers or {}
        self.cb = cb
        self.audit_ledger = audit_ledger
        self.max_cloud_budget_cents = max_cloud_budget_cents

    def resolve_candidates(self, profile: TaskProfile) -> RoutingPlan:
        """Résout le candidat principal et la chaîne de fallback via CanonicalModelRegistry.

        Utilise TaskProfile (task_type, privacy) et la gouvernance par rôles du registre.
        """
        try:
            from core.routing.model_registry import canonical_model_registry
            prefer_local = profile.privacy in (PrivacyRequirement.LOCAL_ONLY, PrivacyRequirement.PREFER_LOCAL)
            must_local = profile.privacy == PrivacyRequirement.LOCAL_ONLY

            target_role = "STANDARD_CHAT"
            if profile.task_type == TaskType.CODING:
                target_role = "LOCAL_CODING" if prefer_local else "CODING"
            elif profile.task_type == TaskType.REASONING:
                target_role = "REASONING"

            rec = canonical_model_registry.get_by_role(target_role)

            if (must_local and rec and rec.provider != "ollama") or not rec:
                local_recs = [m for m in canonical_model_registry.list_models() if m.provider == "ollama"]
                if local_recs:
                    rec = local_recs[0]

            if rec:
                is_local = (rec.provider == "ollama")
                primary = ProviderCandidate(
                    provider_name=rec.provider or ("ollama" if is_local else "gemini"),
                    model_name=rec.name,
                    cost_class=CostClass.LOCAL if is_local else CostClass.CLOUD,
                    capabilities=list(rec.roles) if rec.roles else [rec.role],
                    is_local=is_local,
                )
                return RoutingPlan(primary=primary, fallback_chain=[])
        except Exception:
            pass

        # Fallback de compatibilité (registre indisponible)
        primary = ProviderCandidate(
            provider_name="gemini",
            model_name="gemini-3.5-flash-lite",
            cost_class=CostClass.CLOUD,
            capabilities=["CODING", "GENERAL"],
            is_local=False,
        )
        return RoutingPlan(primary=primary, fallback_chain=[])

    async def execute_task(
        self,
        prompt: str,
        profile: TaskProfile | None = None,
        system_prompt: str = "",
    ) -> ProviderResponse:
        res = await ezzio_master.execute_intent(user_prompt=prompt, system_prompt=system_prompt)
        content = res.get("response", "")
        model = res.get("model", "gemini-3.5-flash-lite")
        provider = res.get("provider", "gemini")
        return ProviderResponse(
            content=content,
            model=model,
            provider=provider,
            ok=res.get("ok", True),
            raw={"coder_federation_trace": {"attempts_count": 1, "exhausted": False}},
        )


coder_federation_router = CoderModelFederationRouter()
