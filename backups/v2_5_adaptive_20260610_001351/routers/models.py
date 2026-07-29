import time
import asyncio
from fastapi import APIRouter
import ollama

from core.model_registry import FAST_MODEL_POOL, load_latency, save_latency

router = APIRouter(prefix="/models", tags=["models"])

def _bench_sync(model):
    started = time.perf_counter()
    response = ollama.chat(
        model=model,
        messages=[{"role": "user", "content": "Réponds exactement: ok"}],
        options={
            "num_gpu": 0,
            "num_ctx": 512,
            "num_predict": 3,
            "temperature": 0,
        },
        keep_alive="20m",
    )
    elapsed_ms = int((time.perf_counter() - started) * 1000)
    return {
        "ok": True,
        "model": model,
        "elapsed_ms": elapsed_ms,
        "response": response["message"]["content"],
    }

async def bench_one(model):
    try:
        result = await asyncio.wait_for(
            asyncio.to_thread(_bench_sync, model),
            timeout=45,
        )
        return result
    except Exception as exc:
        return {
            "ok": False,
            "model": model,
            "error": str(exc),
            "elapsed_ms": 999999,
        }

@router.get("/latency")
async def latency():
    return load_latency()

@router.post("/bench/fast")
async def bench_fast():
    existing = load_latency()
    results = {}

    for model in FAST_MODEL_POOL:
        item = await bench_one(model)
        results[model] = item
        existing[model] = item

    save_latency(existing)

    ordered = sorted(results.values(), key=lambda x: x.get("elapsed_ms", 999999))

    return {
        "results": results,
        "ordered": ordered,
        "best": ordered[0] if ordered else None,
    }
