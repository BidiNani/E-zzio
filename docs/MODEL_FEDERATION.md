# E-ZZIO Model Federation Architecture & Discovery

## 1. Overview
E-ZZIO operates a unified, capability-aware model federation comprising four canonical providers:
1. **LOCAL (Ollama)**: Offline, sovereign edge inference (`qwen3:8b`, `phi4-mini`, `qwen2.5-coder:7b`, etc.)
2. **GEMINI (Google AI Studio)**: High-context multimodal inference (`gemini-2.5-flash`, `gemini-3.7-flash`, `gemini-3.1-pro-preview`) with multi-project token pool rotation.
3. **GROQ (Groq Cloud)**: Ultra-low latency LPU inference (`llama-3.3-70b-versatile`, `llama-3.1-8b-instant`).
4. **NVIDIA (NVIDIA NIM)**: Reasoning and agentic models (`nemotron-3.5-lightning`, `llama-3.1-nemotron-70b-instruct`).

## 2. Federation Core Architecture

### 2.1 Canonical Model Registry (`core/routing/model_registry.py`)
- Standardized taxonomy: `model_id`, `source`, `raw_model_name`, `capabilities`, `context_window`, `cost_class`, `latency_tier`, `qualification_status`.
- Deterministic fallback chains: each model defines an explicit, cycle-free fallback path.
- Cost constraints: Strictly enforces `FREE_ONLY` and `LOCAL` cost tiers.

### 2.2 Dynamic Model Discovery (`tools/discover_models.py`)
- Automated live scanning:
  - Local Ollama daemon (`/api/tags`)
  - Provider environment credentials
- Reconciliation against canonical registry:
  - `LOCAL_CONFIRMED`
  - `LOCAL_MISSING_FROM_RUNTIME`
  - `LOCAL_UNREGISTERED_IN_REGISTRY`
  - `CLOUD_REGISTERED`
- Report generated at `state/audit/model_discovery_report.json`.

### 2.3 Circuit Breaker & Resiliency (`core/routing/circuit_breaker.py`)
- Persistent tri-state tracking: `CLOSED` (normal), `OPEN` (tripped after threshold failures), `HALF_OPEN` (recovery probe).
- Automatic failover when a provider circuit trips.

### 2.4 Health Monitoring (`tools/health_monitor.py`)
- Real-time status reporting: `HEALTHY`, `DEGRADED`, `UNAVAILABLE`, `NOT_CONFIGURED`, `RATE_LIMITED`.
- Persisted at `state/audit/health_status.json`.
