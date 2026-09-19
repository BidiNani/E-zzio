"""Endpoints sante : /health, /ping, /metrics."""
import time

from fastapi import APIRouter

router = APIRouter(tags=["health"])

_start_time = time.time()


@router.get("/health")
@router.get("/ping")
async def health_check():
    return {"ok": True, "status": "ONLINE", "service": "E-ZZIO Sovereign Platform"}


@router.get("/metrics")
async def get_metrics():
    from core.models.provider_health import probe_ollama_status
    ollama_ok = probe_ollama_status()
    return {
        "ok": True,
        "uptime_s": round(time.time() - _start_time, 2),
        "circuit_breaker": "CLOSED",
        "providers_health": {
            "ollama_local": "ONLINE" if ollama_ok else "OFFLINE"
        },
    }
