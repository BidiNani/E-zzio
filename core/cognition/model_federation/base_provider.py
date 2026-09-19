"""E-ZZIO Core — Unified Model & Agent Provider Federation (Phase 4C).

Defines the polymorphic provider interface uniting Local Ollama, Cloud Gemini, and Antigravity Agent.
"""

from __future__ import annotations

import enum
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any


class ProviderDomain(enum.StrEnum):
    LOCAL_OLLAMA = "local_ollama"
    CLOUD_GEMINI = "cloud_gemini"
    CLOUD_GROQ = "cloud_groq"
    AGENT_ANTIGRAVITY = "agent_antigravity"


@dataclass
class FederatedTaskRequest:
    task_id: str
    task_type: str  # "code_refactor", "deep_reasoning", "routine_chat", "vision", "browser_task"
    prompt: str
    domain_preference: ProviderDomain | None = None
    max_tokens: int = 2048
    temperature: float = 0.7
    timeout_seconds: int = 60
    context_metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class FederatedTaskResult:
    task_id: str
    provider_domain: ProviderDomain
    model_name: str
    status: str  # "SUCCESS", "DELEGATED", "FAILED", "REJECTED"
    content: str
    structured_data: dict[str, Any] | None = None
    execution_duration_ms: float = 0.0
    cost_estimate_usd: float = 0.0
    timestamp_utc: str = field(default_factory=lambda: datetime.now(UTC).isoformat())


class BaseFederatedProvider(ABC):
    @property
    @abstractmethod
    def domain(self) -> ProviderDomain:
        pass

    @abstractmethod
    def is_available(self) -> bool:
        pass

    @abstractmethod
    def execute(self, request: FederatedTaskRequest) -> FederatedTaskResult:
        pass
