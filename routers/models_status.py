"""
E-ZZIO - Endpoint de statut live des modeles.
Teste chaque modele et retourne son etat : available / unavailable / unknown.
Cache court (60s) pour eviter le spam.
"""
from __future__ import annotations

import asyncio
import logging
import os
import time
from typing import Any

import httpx
from fastapi import APIRouter

logger = logging.getLogger("EzzioModelsStatus")

router = APIRouter(prefix="/api/models", tags=["models-status"])

# Cache court : le statut change souvent (rate limits, pannes)
_status_cache: dict[str, Any] = {"data": None, "ts": 0.0, "ttl": 60.0}


async def _check_gemini(api_key: str, model_id: str) -> dict:
    try:
        async with httpx.AsyncClient(timeout=5.0) as c:
            url = f"https://generativelanguage.googleapis.com/v1beta/models/{model_id}"
            r = await c.get(url, headers={"x-goog-api-key": api_key})
            if r.status_code == 200:
                return {"status": "available", "error": None}
            return {"status": "unavailable", "error": f"HTTP {r.status_code}"}
    except httpx.TimeoutException:
        return {"status": "unknown", "error": "timeout"}
    except Exception as e:
        return {"status": "unknown", "error": str(e)[:100]}


async def _check_openrouter(api_key: str, model_id: str) -> dict:
    try:
        async with httpx.AsyncClient(timeout=8.0) as c:
            body = {
                "model": model_id,
                "messages": [{"role": "user", "content": "hi"}],
                "max_tokens": 1,
            }
            r = await c.post(
                "https://openrouter.ai/api/v1/chat/completions",
                headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
                json=body,
            )
            if r.status_code == 200:
                return {"status": "available", "error": None}
            if r.status_code == 429:
                return {"status": "unavailable", "error": "rate_limit"}
            if r.status_code == 402:
                return {"status": "unavailable", "error": "payment_required"}
            if r.status_code == 404:
                return {"status": "unavailable", "error": "model_not_found"}
            return {"status": "unavailable", "error": f"HTTP {r.status_code}"}
    except httpx.TimeoutException:
        return {"status": "unknown", "error": "timeout"}
    except Exception as e:
        return {"status": "unknown", "error": str(e)[:100]}


async def _check_groq(api_key: str, model_id: str) -> dict:
    try:
        async with httpx.AsyncClient(timeout=8.0) as c:
            body = {
                "model": model_id,
                "messages": [{"role": "user", "content": "hi"}],
                "max_tokens": 1,
            }
            r = await c.post(
                "https://api.groq.com/openai/v1/chat/completions",
                headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
                json=body,
            )
            if r.status_code == 200:
                return {"status": "available", "error": None}
            if r.status_code == 429:
                return {"status": "unavailable", "error": "rate_limit"}
            return {"status": "unavailable", "error": f"HTTP {r.status_code}"}
    except httpx.TimeoutException:
        return {"status": "unknown", "error": "timeout"}
    except Exception as e:
        return {"status": "unknown", "error": str(e)[:100]}


async def _check_ollama(model_id: str) -> dict:
    base = os.getenv("OLLAMA_BASE_URL", "http://127.0.0.1:11434")
    try:
        async with httpx.AsyncClient(timeout=10.0) as c:
            body = {"model": model_id, "prompt": "", "stream": False}
            r = await c.post(f"{base}/api/generate", json=body)
            if r.status_code == 200:
                return {"status": "available", "error": None}
            return {"status": "unavailable", "error": f"HTTP {r.status_code}"}
    except httpx.TimeoutException:
        return {"status": "unknown", "error": "timeout"}
    except Exception as e:
        return {"status": "unknown", "error": str(e)[:100]}


async def _check_nvidia(api_key: str, model_id: str) -> dict:
    try:
        async with httpx.AsyncClient(timeout=8.0) as c:
            body = {
                "model": model_id,
                "messages": [{"role": "user", "content": "hi"}],
                "max_tokens": 1,
            }
            r = await c.post(
                "https://integrate.api.nvidia.com/v1/chat/completions",
                headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
                json=body,
            )
            if r.status_code == 200:
                return {"status": "available", "error": None}
            if r.status_code == 429:
                return {"status": "unavailable", "error": "rate_limit"}
            return {"status": "unavailable", "error": f"HTTP {r.status_code}"}
    except httpx.TimeoutException:
        return {"status": "unknown", "error": "timeout"}
    except Exception as e:
        return {"status": "unknown", "error": str(e)[:100]}


async def _check_one(provider: str, model_id: str, keys: dict) -> dict:
    if provider == "gemini":
        return await _check_gemini(keys.get("gemini", ""), model_id)
    if provider == "openrouter":
        return await _check_openrouter(keys.get("openrouter", ""), model_id)
    if provider == "groq":
        return await _check_groq(keys.get("groq", ""), model_id)
    if provider == "ollama":
        return await _check_ollama(model_id)
    if provider == "nvidia":
        return await _check_nvidia(keys.get("nvidia", ""), model_id)
    return {"status": "unknown", "error": f"provider_inconnu: {provider}"}


@router.get("/status")
async def models_status(force_refresh: bool = False) -> dict[str, Any]:
    """Retourne le statut live de chaque modele (cache 60s)."""
    now = time.time()
    if not force_refresh and _status_cache["data"] and now - _status_cache["ts"] < _status_cache["ttl"]:
        cached = dict(_status_cache["data"])
        cached["cached"] = True
        cached["age_sec"] = round(now - _status_cache["ts"], 1)
        return cached

    try:
        from core.config.secrets_loader import gemini_keys
        gemini_k = gemini_keys()
        gemini_key = gemini_k[0] if gemini_k else ""
    except Exception:
        gemini_key = ""

    keys = {
        "gemini": gemini_key,
        "openrouter": os.getenv("OPENROUTER_API_KEY", ""),
        "groq": os.getenv("GROQ_API_KEY", ""),
        "nvidia": os.getenv("NVIDIA_API_KEY", ""),
    }

    from routers.models import all_models as get_all_models
    models_data = await get_all_models(force_refresh=False)

    result: dict[str, Any] = {"cached": False, "ts": now}

    for provider in ["gemini", "groq", "openrouter", "ollama", "nvidia"]:
        models = models_data.get(provider, [])
        if not isinstance(models, list) or not models:
            result[provider] = {}
            continue

        free = [m for m in models if m.get("free")]
        paid = [m for m in models if not m.get("free")]
        to_test = (free[:10] + paid[:5])[:15]

        sem = asyncio.Semaphore(3)

        async def test_with_sem(m, _sem=sem, _provider=provider, _keys=keys):
            async with _sem:
                return await _check_one(_provider, m["id"], _keys)

        tasks = [test_with_sem(m) for m in to_test]
        statuses = await asyncio.gather(*tasks, return_exceptions=True)

        provider_status = {}
        for m, status in zip(to_test, statuses, strict=True):
            if isinstance(status, Exception):
                provider_status[m["id"]] = {"status": "unknown", "error": str(status)[:100]}
            else:
                provider_status[m["id"]] = status

        result[provider] = provider_status

    _status_cache["data"] = result
    _status_cache["ts"] = now
    return result
