from enum import Enum
from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional

class ModelHealthStatus(str, Enum):
    HEALTHY = "HEALTHY"
    DEGRADED = "DEGRADED"
    UNAVAILABLE = "UNAVAILABLE"
    QUARANTINED = "QUARANTINED"

class ModelProfile(BaseModel):
    model_id: str
    name: str
    provider: str
    capabilities: List[str]
    context_window: int
    local: bool
    estimated_latency_ms: int
    cost_class: str
    quality_score: float
    reliability_score: float
    security_class: str
    health: ModelHealthStatus = ModelHealthStatus.HEALTHY
    enabled: bool = True

REAL_OLLAMA_MODEL_CATALOG: Dict[str, ModelProfile] = {
    "qwen2.5-coder:14b": ModelProfile(
        model_id="qwen2.5-coder:14b",
        name="Qwen 2.5 Coder 14B (Local)",
        provider="ollama",
        capabilities=["code", "powershell", "python", "debug", "refactor", "structured_json"],
        context_window=32768,
        local=True,
        estimated_latency_ms=750,
        cost_class="free",
        quality_score=0.98,
        reliability_score=0.97,
        security_class="local_isolated",
        health=ModelHealthStatus.HEALTHY,
        enabled=True
    ),
    "qwen3:8b": ModelProfile(
        model_id="qwen3:8b",
        name="Qwen 3 8B (Local)",
        provider="ollama",
        capabilities=["reasoning", "general", "chat", "analysis", "forensic"],
        context_window=32768,
        local=True,
        estimated_latency_ms=520,
        cost_class="free",
        quality_score=0.95,
        reliability_score=0.96,
        security_class="local_isolated",
        health=ModelHealthStatus.HEALTHY,
        enabled=True
    ),
    "qwen3:14b": ModelProfile(
        model_id="qwen3:14b",
        name="Qwen 3 14B (Local)",
        provider="ollama",
        capabilities=["reasoning", "forensic", "analysis", "code", "long_context"],
        context_window=65536,
        local=True,
        estimated_latency_ms=880,
        cost_class="free",
        quality_score=0.97,
        reliability_score=0.96,
        security_class="local_isolated",
        health=ModelHealthStatus.HEALTHY,
        enabled=True
    ),
    "hf.co/mradermacher/Kiwi-4b-i1-GGUF:Q4_K_M": ModelProfile(
        model_id="hf.co/mradermacher/Kiwi-4b-i1-GGUF:Q4_K_M",
        name="Kiwi 4B (Ultra-Fast Local)",
        provider="ollama",
        capabilities=["fast_reply", "chat", "fast_chat"],
        context_window=8192,
        local=True,
        estimated_latency_ms=210,
        cost_class="free",
        quality_score=0.88,
        reliability_score=0.95,
        security_class="local_isolated",
        health=ModelHealthStatus.HEALTHY,
        enabled=True
    ),
    "granite4.1:8b": ModelProfile(
        model_id="granite4.1:8b",
        name="IBM Granite 4.1 8B (Enterprise)",
        provider="ollama",
        capabilities=["structured_json", "extraction", "summarization", "enterprise"],
        context_window=32768,
        local=True,
        estimated_latency_ms=540,
        cost_class="free",
        quality_score=0.94,
        reliability_score=0.97,
        security_class="local_isolated",
        health=ModelHealthStatus.HEALTHY,
        enabled=True
    ),
    "groq/llama-3.3-70b-versatile": ModelProfile(
        model_id="groq/llama-3.3-70b-versatile",
        name="Llama 3.3 70B (Groq Cloud)",
        provider="groq",
        capabilities=["research", "fast_reply", "chat", "reasoning"],
        context_window=128000,
        local=False,
        estimated_latency_ms=260,
        cost_class="low",
        quality_score=0.98,
        reliability_score=0.99,
        security_class="cloud_tls",
        health=ModelHealthStatus.HEALTHY,
        enabled=True
    )
}
