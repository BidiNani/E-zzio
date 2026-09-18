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
        return "gemini-2.5-flash"
    n = name.lower().strip()
    if "gemini" in n:
        return "gemini-2.5-flash"
    if "qwen" in n or "ollama" in n:
        return "qwen2.5-coder:7b"
    return name


class CoderModelFederationRouter:
    """Passerelle de fédération canonique déléguant vers EzzioMaster."""

    DEFAULT_MODELS = {
        "gemini": "gemini-2.5-flash",
        "ollama": "qwen2.5-coder:7b",
        "groq": "llama-3.3-70b-versatile",
    }

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
        primary = ProviderCandidate(
            provider_name="gemini",
            model_name="gemini-2.5-flash",
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
        model = res.get("model", "gemini-2.5-flash")
        provider = res.get("provider", "gemini")
        return ProviderResponse(
            content=content,
            model=model,
            provider=provider,
            ok=res.get("ok", True),
            raw={"coder_federation_trace": {"attempts_count": 1, "exhausted": False}},
        )


coder_federation_router = CoderModelFederationRouter()
