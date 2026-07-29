from fastapi import APIRouter
from core.dispatcher import ezzio_dispatcher
from core.model_registry import all_known_models, load_latency
from core.telemetry import read_events

router = APIRouter(tags=["system"])

@router.get("/")
async def root_status():
    return {
        "name": "E-ZZIO",
        "version": "v2.6-autonomic-tactical-core",
        "status": "alive",
        "gpu_policy": "disabled_for_ezzio",
        "num_gpu": 0,
    }

@router.get("/status")
async def status():
    return ezzio_dispatcher.status()

@router.get("/health")
async def health():
    return {
        "ok": True,
        "service": "ezzio-api",
        "version": "v2.6-autonomic-tactical-core",
        "gpu_policy": "disabled_for_ezzio",
        "num_gpu": 0,
    }

@router.get("/models")
async def models():
    return {
        "known_models": all_known_models(),
        "latency": load_latency(),
    }

@router.get("/telemetry/recent")
async def telemetry_recent(limit: int = 100):
    return {"items": read_events(limit=limit)}
