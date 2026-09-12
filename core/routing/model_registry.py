"""
core/routing/model_registry.py — Compatibility re-exports for canonical model registry
"""
from enum import Enum, auto
from dataclasses import dataclass, field
from typing import List, Optional

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
    roles: List[str] = field(default_factory=list)
    thinking_level: str = "off"

    def __post_init__(self):
        if self.role and self.role not in self.roles:
            self.roles.append(self.role)

class CanonicalModelRegistry:
    def __init__(self):
        self._models = [
            CanonicalModelRecord("gemini-3.8-flash", ModelSource.GEMINI, role="MASTER", roles=["MASTER", "MASTER_STRATEGIC"], thinking_level="high"),
            CanonicalModelRecord("gemini-3.7-flash", ModelSource.GEMINI, role="CODING", roles=["CODING"], thinking_level="low"),
            CanonicalModelRecord("gemini-3.6-flash", ModelSource.GEMINI, role="STANDARD_CHAT", roles=["STANDARD_CHAT", "FAST_CHAT", "FORENSIC"], thinking_level="medium"),
            CanonicalModelRecord("gemini-3.5-flash", ModelSource.GEMINI, role="REFACTOR", roles=["REFACTOR"], thinking_level="medium"),
            CanonicalModelRecord("gemini-2.5-flash", ModelSource.GEMINI, role="FALLBACK", roles=["FALLBACK"], thinking_level="off"),
            CanonicalModelRecord("qwen2.5-coder:7b-instruct-q4_K_M", ModelSource.LOCAL, role="LOCAL", roles=["LOCAL", "LOCAL_CODING"]),
            CanonicalModelRecord("minicpm5-2b-godot:latest", ModelSource.LOCAL, role="FAST", roles=["FAST", "FAST_LOCAL"]),
            CanonicalModelRecord("phi4-mini:latest", ModelSource.LOCAL, role="LOCAL_MINI", roles=["LOCAL_MINI"]),
            CanonicalModelRecord("nemotron-3-nano:4b", ModelSource.LOCAL, role="LOCAL_THINKING", roles=["LOCAL_THINKING"], thinking_level="low"),
            CanonicalModelRecord("hermes3:8b", ModelSource.LOCAL, role="LOCAL_AGENT", roles=["LOCAL_AGENT"]),
        ]

    def list_models(self, qualified_only: bool = True, include_disabled: bool = False):
        return self._models

    def get(self, name: str) -> Optional[CanonicalModelRecord]:
        for m in self._models:
            if m.name == name:
                return m
        return CanonicalModelRecord(name=name)

    def get_by_role(self, role: str) -> Optional[CanonicalModelRecord]:
        for m in self._models:
            if role in m.roles or m.role == role:
                return m
        return None

canonical_model_registry = CanonicalModelRegistry()
