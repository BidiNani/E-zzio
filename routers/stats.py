import os
import time
import logging
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException
from fastapi.security.api_key import APIKeyHeader
from pydantic import BaseModel
from typing import Dict, Optional
import asyncio

logger = logging.getLogger("ezzio.routers.stats")

API_KEY_NAME = "X-API-Key"
api_key_header = APIKeyHeader(name=API_KEY_NAME, auto_error=False)
EXPECTED_KEY = os.getenv("EZZIO_API_KEY", "ezzio_secret_key_local_dev")

router = APIRouter()

# --- Stockage en mémoire ---
stats_data = {"total_requests": 0, "requests_by_provider": {}, "latencies": [], "last_updated": None}

# Buffer de logs pour écriture asynchrone
LOG_BUFFER = []
LOG_FLUSH_INTERVAL = 5  # secondes


async def flush_logs_periodically():
    while True:
        await asyncio.sleep(LOG_FLUSH_INTERVAL)
        if LOG_BUFFER:
            # Ici, tu peux écrire dans un fichier ou DB
            # Exemple simple: logger (à remplacer par ton vrai stockage)
            for entry in LOG_BUFFER:
                logger.info(f"Stats flush: {entry}")
            LOG_BUFFER.clear()


# Démarrer la tâche de flush au démarrage du router
async def init_stats_router():
    asyncio.create_task(flush_logs_periodically())


# --- Modèles ---
class StatsResponse(BaseModel):
    total_requests: int
    avg_latency_ms: Optional[float]
    top_provider: Optional[str]
    requests_by_provider: Dict[str, int]
    last_updated: Optional[str]


class StatsNotify(BaseModel):
    provider: str
    latency_ms: float


# --- Helpers ---
def get_stats_summary() -> StatsResponse:
    total = stats_data["total_requests"]
    latencies = stats_data["latencies"]
    avg_lat = sum(latencies) / len(latencies) if latencies else None

    by_provider = stats_data["requests_by_provider"]
    top_prov = max(by_provider, key=by_provider.get) if by_provider else None

    return StatsResponse(
        total_requests=total,
        avg_latency_ms=avg_lat,
        top_provider=top_prov,
        requests_by_provider=by_provider,
        last_updated=stats_data["last_updated"],
    )


# --- Endpoints ---
@router.get("/api/v1/stats", response_model=StatsResponse, tags=["Stats"])
async def get_stats(api_key: str = Depends(api_key_header)):
    if api_key != EXPECTED_KEY:
        raise HTTPException(status_code=403, detail="Clé API invalide")
    return get_stats_summary()


@router.post("/api/v1/stats/notify", tags=["Stats"])
async def notify_stats(data: StatsNotify, api_key: str = Depends(api_key_header)):
    if api_key != EXPECTED_KEY:
        raise HTTPException(status_code=403, detail="Clé API invalide")

    stats_data["total_requests"] += 1
    stats_data["requests_by_provider"][data.provider] = stats_data["requests_by_provider"].get(data.provider, 0) + 1
    stats_data["latencies"].append(data.latency_ms)
    stats_data["latencies"] = stats_data["latencies"][-100:]  # garder seulement les 100 dernières
    stats_data["last_updated"] = datetime.now().isoformat()

    # Log bufferisé
    LOG_BUFFER.append({"provider": data.provider, "latency_ms": data.latency_ms, "ts": time.time()})

    return {"status": "ok"}
