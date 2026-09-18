"""
routers/search.py — Recherche web multi-provider.

Providers supportés :
  - serpdive    : API officielle (gratuit illimité avec krill)
  - tavily      : API officielle (1K/mois gratuit)
  - duckduckgo  : via ddgs (scraping gratuit)
  - google      : via ddgs (scraping gratuit)
  - brave       : via ddgs (scraping gratuit)
"""
from __future__ import annotations

import logging
import os
from pathlib import Path
from typing import Any

import httpx
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

logger = logging.getLogger("SearchRouter")

router = APIRouter(prefix="/api/web-search", tags=["search"])

_ROOT = Path(__file__).resolve().parents[1]


def _read_secret(key: str) -> str | None:
    """Lit une clé depuis secrets/.env."""
    env_path = _ROOT / "secrets" / ".env"
    if env_path.exists():
        try:
            for line in env_path.read_text(encoding="utf-8").splitlines():
                line = line.strip()
                if line.startswith("#") or "=" not in line:
                    continue
                k, _, v = line.partition("=")
                if k.strip() == key:
                    val = v.strip().strip("\"'")
                    return val or None
        except Exception:
            pass
    return os.environ.get(key) or None


class SearchRequest(BaseModel):
    query: str
    provider: str = "serpdive"
    max_results: int = 5
    model: str = "krill"  # pour serpdive: krill | mako | moby


async def _search_serpdive(query: str, max_results: int, model: str) -> dict[str, Any]:
    """SERPdive — API officielle. Modèle krill = gratuit illimité."""
    api_key = _read_secret("SERPDIVE_API_KEY")
    if not api_key:
        return {"ok": False, "error": "SERPDIVE_API_KEY manquante dans secrets/.env"}

    # L'API SERPdive est accessible via https://api.serpdive.com/v1/search
    # On utilise le modèle krill par défaut (gratuit)
    url = "https://api.serpdive.com/v1/search"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    payload = {
        "query": query,
        "model": model,
        "max_results": max_results,
    }

    async with httpx.AsyncClient(timeout=30.0) as client:
        try:
            r = await client.post(url, json=payload, headers=headers)
            if r.status_code == 401:
                return {"ok": False, "error": "SERPDIVE_API_KEY invalide (401)"}
            if r.status_code == 429:
                return {"ok": False, "error": "SERPdive rate limit (429) — réessayer plus tard"}
            r.raise_for_status()
            data = r.json()
        except httpx.HTTPStatusError as exc:
            return {"ok": False, "error": f"HTTP {exc.response.status_code}: {exc.response.text[:200]}"}
        except Exception as exc:
            return {"ok": False, "error": f"Erreur réseau : {exc}"}

    return {"ok": True, "provider": "serpdive", "data": data}


async def _search_tavily(query: str, max_results: int) -> dict[str, Any]:
    """Tavily — API officielle."""
    api_key = _read_secret("TAVILY_API_KEY")
    if not api_key:
        return {"ok": False, "error": "TAVILY_API_KEY manquante"}

    url = "https://api.tavily.com/search"
    payload = {
        "api_key": api_key,
        "query": query,
        "max_results": max_results,
        "search_depth": "basic",
        "include_answer": False,
    }

    async with httpx.AsyncClient(timeout=30.0) as client:
        try:
            r = await client.post(url, json=payload)
            r.raise_for_status()
            data = r.json()
        except Exception as exc:
            return {"ok": False, "error": f"Tavily : {exc}"}

    return {"ok": True, "provider": "tavily", "data": data}


async def _search_ddgs(query: str, max_results: int, backend: str) -> dict[str, Any]:
    """DuckDuckGo / Google / Brave via ddgs (scraping gratuit)."""
    try:
        from ddgs import DDGS
    except ImportError:
        return {"ok": False, "error": "ddgs non installé. Lancer : pip install ddgs"}

    # ddgs supporte backend="duckduckgo" | "google" | "brave" | "bing" etc.
    backend_map = {
        "duckduckgo": "duckduckgo",
        "google": "google",
        "brave": "brave",
    }
    be = backend_map.get(backend, "duckduckgo")

    try:
        results = []
        with DDGS() as ddgs:
            for r in ddgs.text(query, max_results=max_results, backend=be):
                results.append({
                    "url": r.get("href", ""),
                    "title": r.get("title", ""),
                    "content": r.get("body", ""),
                })
        return {
            "ok": True,
            "provider": backend,
            "data": {
                "results": results,
                "total": len(results),
            },
        }
    except Exception as exc:
        return {"ok": False, "error": f"{backend} : {exc}"}


@router.post("")
async def api_search(req: SearchRequest):
    _ck = _cache_key(req.provider, req.query, req.max_results, req.model)
    _hit = _cache_get(_ck)
    if _hit is not None:
        _hit["cached"] = True
        return _hit
    """Recherche web multi-provider."""
    provider = req.provider.lower().strip()
    query = req.query.strip()

    if not query:
        raise HTTPException(status_code=400, detail="query vide")

    if provider == "serpdive":
        # SERPdive : leur API retourne systématiquement 502 depuis 2026-09-18
        # On retourne un message clair au lieu de faire la requête
        return {
            "ok": False,
            "provider": "serpdive",
            "error": "SERPdive est actuellement indisponible côté API (502 search_failed). Utilise Brave, Tavily ou DuckDuckGo.",
        }
    elif provider == "tavily":
        result = await _search_tavily(query, req.max_results)
    elif provider in ("duckduckgo", "google", "brave"):
        result = await _search_ddgs(query, req.max_results, provider)
    else:
        raise HTTPException(status_code=400, detail=f"Provider inconnu : {provider}")

    if not result.get("ok"):
        return {"ok": False, "error": result.get("error", "Erreur inconnue"), "provider": provider}

    _response = {
        "ok": True,
        "data": {
            "provider": provider,
            "data": result["data"],
        },
    }
    _cache_put(_ck, _response)
    return _response
# ============================================================
# CACHE LRU (5 minutes)
# ============================================================
import hashlib as _hashlib
import time as _time
from collections import OrderedDict as _OrderedDict

_CACHE_MAX = 128
_CACHE_TTL = 300  # secondes
_cache: _OrderedDict[str, tuple[float, dict]] = _OrderedDict()


def _cache_key(provider: str, query: str, max_results: int, model: str) -> str:
    raw = f"{provider}|{query.lower().strip()}|{max_results}|{model}"
    return _hashlib.sha256(raw.encode("utf-8")).hexdigest()[:24]


def _cache_get(key: str):
    entry = _cache.get(key)
    if not entry:
        return None
    ts, value = entry
    if _time.time() - ts > _CACHE_TTL:
        _cache.pop(key, None)
        return None
    _cache.move_to_end(key)
    return value


def _cache_put(key: str, value: dict) -> None:
    _cache[key] = (_time.time(), value)
    _cache.move_to_end(key)
    while len(_cache) > _CACHE_MAX:
        _cache.popitem(last=False)


def cache_stats() -> dict:
    return {"size": len(_cache), "max": _CACHE_MAX, "ttl_s": _CACHE_TTL}


@router.get("/cache/stats")
async def api_cache_stats():
    """Statistiques du cache de recherche."""
    return {"ok": True, "cache": cache_stats()}
