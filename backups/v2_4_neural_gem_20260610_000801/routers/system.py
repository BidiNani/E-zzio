from fastapi import APIRouter
from core.dispatcher import ezzio_dispatcher

router = APIRouter(tags=["system"])

@router.get("/")
async def root_status():
    return {
        "name": "E-ZZIO",
        "version": "v2.3-pro-async-routers",
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
        "version": "v2.3-pro-async-routers",
        "gpu_policy": "disabled_for_ezzio",
        "num_gpu": 0,
    }
