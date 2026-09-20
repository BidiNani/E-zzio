"""
core/routing/model_registry.py — Compatibility re-exports for canonical model registry
"""
from dataclasses import dataclass, field
from enum import Enum, auto

from core.routing.local_registry import LOCAL_MODELS as _LOCAL_MODELS


class ModelSource(Enum):
    LOCAL = auto()
    GEMINI = auto()
    GROQ = auto()
    NVIDIA = auto()

class LatencyTier(Enum):
    ULTRA_FAST = auto()
    FAST = auto()
    MEDIUM = auto()
    SLOW = auto()

class ModelQualificationStatus(Enum):
    QUALIFIED = auto()
    DISQUALIFIED = auto()
    DISABLED = auto()
    EXPERIMENTAL = auto()

@dataclass
class CanonicalModelRecord:
    name: str
    source: ModelSource = ModelSource.GEMINI
    latency_tier: LatencyTier = LatencyTier.FAST
    qualification_status: ModelQualificationStatus = ModelQualificationStatus.QUALIFIED
    enabled: bool = True
    role: str = "general"
    roles: list[str] = field(default_factory=list)
    thinking_level: str = "off"

    def __post_init__(self):
        if self.role and self.role not in self.roles:
            self.roles.append(self.role)

class CanonicalModelRegistry:
    def __init__(self):
        self._models = [
            CanonicalModelRecord("gemini-3.8-flash", ModelSource.GEMINI, role="MASTER", roles=["MASTER", "MASTER_STRATEGIC"], thinking_level="high"),
            CanonicalModelRecord("gemini-3.7-flash", ModelSource.GEMINI, role="CODING", roles=["CODING"], thinking_level="low"),
            CanonicalModelRecord("gemini-3.6-flash", ModelSource.GEMINI, role="FORENSIC", roles=["FORENSIC"], thinking_level="medium"),
            CanonicalModelRecord("gemini-3.5-flash-lite", ModelSource.GEMINI, role="STANDARD_CHAT", roles=["STANDARD_CHAT", "FAST_CHAT", "FAST", "FALLBACK"], thinking_level="medium"),
            CanonicalModelRecord("gemini-3.5-flash", ModelSource.GEMINI, role="REFACTOR", roles=["REFACTOR"], thinking_level="medium"),
            CanonicalModelRecord("qwen2.5-coder:7b-instruct-q4_K_M", ModelSource.LOCAL, role="LOCAL", roles=["LOCAL", "LOCAL_CODING"]),
            CanonicalModelRecord("qwen3.5-mtp:4b", ModelSource.LOCAL, role="FAST_LOCAL", roles=["FAST_LOCAL"]),
            CanonicalModelRecord("phi4-mini:latest", ModelSource.LOCAL, role="LOCAL_MINI", roles=["LOCAL_MINI"]),
            CanonicalModelRecord("nemotron-3-nano:4b", ModelSource.LOCAL, role="LOCAL_THINKING", roles=["LOCAL_THINKING"], thinking_level="low"),
            CanonicalModelRecord("hermes3:8b", ModelSource.LOCAL, role="LOCAL_AGENT", roles=["LOCAL_AGENT"]),
        ]

    def list_models(self, qualified_only: bool = True, include_disabled: bool = False):
        return self._models

    def get(self, name: str) -> CanonicalModelRecord | None:
        for m in self._models:
            if m.name == name:
                return m
        return None

    def get_by_role(self, role: str) -> CanonicalModelRecord | None:
        for m in self._models:
            if role in m.roles or m.role == role:
                return m
        return None


    def _check_local_sync(self) -> list[str]:
        """Détecte les modèles locaux déclarés mais absents du registre."""
        local_declared = {m.id for m in _LOCAL_MODELS}
        registry_locals = {
            r.model_id for r in self._records
            if hasattr(r, "source") and str(r.source).endswith("LOCAL")
        }
        return list(local_declared - registry_locals)

canonical_model_registry = CanonicalModelRegistry()
