"""Endpoints santé : /health, /ping, /metrics."""
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
    return {"uptime_s": round(time.time() - _start_time, 2)}
