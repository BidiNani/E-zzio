from dataclasses import dataclass, field
from typing import Optional, Dict, Any


@dataclass
class ModelRequest:
    prompt: str
    task: str = "general"  # general, code, vision, reasoning
    complexity: str = "low"  # low, medium, high, critical
    latency: str = "normal"  # fast, normal
    budget: str = "local_first"  # local_first, cloud_first, offline_only
    system_prompt: Optional[str] = None
    parameters: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ModelResponse:
    content: str
    model_used: str
    provider_used: str
    tokens_evaluated: int = 0
    tokens_generated: int = 0
    latency_ms: float = 0.0
    fallback_applied: bool = False
    metadata: Dict[str, Any] = field(default_factory=dict)
