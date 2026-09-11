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

class CanonicalModelRegistry:
    def __init__(self):
        self._models = [
            CanonicalModelRecord("gemini-3.7-flash", ModelSource.GEMINI),
            CanonicalModelRecord("gemini-3.6-flash", ModelSource.GEMINI),
            CanonicalModelRecord("qwen2.5-coder:7b", ModelSource.LOCAL),
            CanonicalModelRecord("llama-3.3-70b-versatile", ModelSource.GROQ),
        ]

    def list_models(self, qualified_only: bool = True, include_disabled: bool = False):
        return self._models

    def get(self, name: str) -> Optional[CanonicalModelRecord]:
        for m in self._models:
            if m.name == name:
                return m
        return CanonicalModelRecord(name=name)

canonical_model_registry = CanonicalModelRegistry()
