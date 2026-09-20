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

from core.models.provider_http import PROVIDERS, get_api_key

logger = logging.getLogger("EzzioModelsStatus")

router = APIRouter(prefix="/api/models", tags=["models-status"])

# Cache court : le statut change souvent (rate limits, pannes)
_status_cache: dict[str, Any] = {"data": None, "ts": 0.0, "ttl": 60.0}


async def _check_gemini(api_key: str, model_id: str) -> dict:
    """Test chat : POST generateContent avec un prompt minimal."""
    try:
        async with httpx.AsyncClient(timeout=8.0) as c:
            url = f"https://generativelanguage.googleapis.com/v1beta/models/{model_id}:generateContent"
            body = {
                "contents": [{"parts": [{"text": "hi"}]}],
                "generationConfig": {"maxOutputTokens": 1},
            }
            r = await c.post(url, headers={"x-goog-api-key": api_key, "Content-Type": "application/json"}, json=body)
            if r.status_code == 200:
                # Verifier que la reponse contient du TEXTE (pas audio/image)
                data = r.json()
                candidates = data.get("candidates", [])
                if candidates:
                    parts = candidates[0].get("content", {}).get("parts", [])
                    for part in parts:
                        if "text" in part:
                            return {"status": "available", "error": None}
                return {"status": "unavailable", "error": "non_chat_model"}
            if r.status_code == 404:
                return {"status": "unavailable", "error": "model_not_found"}
            if r.status_code == 429:
                return {"status": "unavailable", "error": "rate_limit"}
            if r.status_code == 400:
                return {"status": "unavailable", "error": "bad_request"}
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
                data = r.json()
                choices = data.get("choices", [])
                if choices and choices[0].get("message", {}).get("content"):
                    return {"status": "available", "error": None}
                return {"status": "unavailable", "error": "empty_response"}
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
    """Test chat : POST chat/completions."""
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
                data = r.json()
                choices = data.get("choices", [])
                if choices and choices[0].get("message", {}).get("content"):
                    return {"status": "available", "error": None}
                return {"status": "unavailable", "error": "empty_response"}
            if r.status_code == 404:
                return {"status": "unavailable", "error": "model_not_found"}
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
    """Statut live des modeles (health-check rapide).

    Strategie :
      - 3 modeles par provider (au lieu de 15)
      - Parallelisme 15 (au lieu de 3)
      - Timeout court
      - Seuls les providers rapides (gemini/groq/openrouter) sont testes
        automatiquement. Ollama et NVIDIA sont marques "untested" par defaut
        (ils peuvent etre testes plus tard via un endpoint dedie).
    """
    now = time.time()
    if not force_refresh and _status_cache["data"] and now - _status_cache["ts"] < _status_cache["ttl"]:
        cached = dict(_status_cache["data"])
        cached["cached"] = True
        cached["age_sec"] = round(now - _status_cache["ts"], 1)
        return cached

    # Providers rapides uniquement (eviter les timeouts longs)
    FAST_PROVIDERS = ["gemini", "groq", "openrouter"]

    from routers.models import all_models as get_all_models
    models_data = await get_all_models(force_refresh=False)

    result: dict[str, Any] = {"cached": False, "ts": now}

    # Marquer les providers lents comme "untested" (pas de health-check)
    for slow in ["ollama", "nvidia"]:
        result[slow] = {"__info__": {"status": "unknown", "error": "not_checked"}}

    for provider in FAST_PROVIDERS:
        models = models_data.get(provider, [])
        if not isinstance(models, list) or not models:
            result[provider] = {}
            continue

        # Prendre 3 modeles gratuits + 1 payant (max 4)
        free = [m for m in models if m.get("free")]
        paid = [m for m in models if not m.get("free")]
        to_test = (free[:3] + paid[:1])[:4]

        # Parallelisme fort
        sem = asyncio.Semaphore(15)

        async def test_with_sem(m, _sem=sem, _provider=provider):
            async with _sem:
                spec = PROVIDERS.get(_provider)
                if not spec:
                    return {"status": "unknown", "error": "no_provider"}
                api_key = get_api_key(_provider)
                try:
                    return await asyncio.wait_for(
                        spec.check(api_key, m["id"]),
                        timeout=5.0,
                    )
                except TimeoutError:
                    return {"status": "unknown", "error": "timeout"}

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
