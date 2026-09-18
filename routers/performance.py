from fastapi import APIRouter
from pydantic import BaseModel

from core.pc_optimizer import (
    bench_model,
    ollama_tags,
    pc_profile,
    performance_status,
    quick_bench,
    warmup_profile,
)

router = APIRouter(prefix="/performance", tags=["performance"])


class WarmupRequest(BaseModel):
    level: str = "fast"


class BenchRequest(BaseModel):
    model: str = "qwen3:1.7b"
    prompt: str = "Explique en une phrase le rôle d'E-ZZIO."
    predict: int = 80


@router.get("/status")
async def performance_get_status():
    return performance_status()


@router.get("/pc")
async def performance_get_pc():
    return pc_profile()


@router.get("/ollama")
async def performance_get_ollama():
    return ollama_tags()


@router.post("/warmup")
async def performance_post_warmup(req: WarmupRequest):
    return warmup_profile(req.level)


@router.post("/bench")
async def performance_post_bench(req: BenchRequest):
    return bench_model(req.model, req.prompt, req.predict)


@router.post("/bench/quick")
async def performance_post_bench_quick():
    return quick_bench()
