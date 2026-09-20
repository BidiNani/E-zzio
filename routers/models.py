"""
E-ZZIO — Endpoint unifié de liste des modèles multi-providers.
Enrichi avec prix, gratuité, et quotas (quand disponibles).
"""
from __future__ import annotations

import os
import re
import time
from typing import Any

import httpx
from fastapi import APIRouter

from core.models.provider_specs import PROVIDERS, get_api_key
from core.routing.registry import all_models as _all_models

router = APIRouter(prefix="/api/models", tags=["models"])

_cache: dict[str, Any] = {"data": None, "ts": 0.0, "ttl": 3600.0}


# ----------------------------------------------------------------------------
# Support thinking
# ----------------------------------------------------------------------------
# THINKING_CAPABLE : construit dynamiquement depuis le registre canonique.
# Les modèles cloud viennent de providers_registry (source unique de vérité).
# Les modèles locaux (Ollama) sont ajoutés manuellement car hors scope cloud.
THINKING_CAPABLE = {
    m.id: {"method": m.thinking_method, "levels": list(m.thinking_levels)}
    for m in _all_models()
    if m.thinking_method != "none"
}

# Modèles locaux (Ollama) — source unique : core/routing/local_registry.py
from core.routing.registry import thinking_capable as _local_thinking

THINKING_CAPABLE.update(_local_thinking())


@router.get("/thinking-support")
async def thinking_support(model: str) -> dict[str, Any]:
    for prefix, info in THINKING_CAPABLE.items():
        if model.startswith(prefix):
            return {"supported": True, **info, "model": model}
    return {"supported": False, "method": None, "levels": [], "model": model}


# ----------------------------------------------------------------------------
# Helpers : parsing prix
# ----------------------------------------------------------------------------
def _is_free_pricing(pricing: dict) -> bool:
    """OpenRouter : gratuit si prompt ET completion == 0."""
    try:
        p = float(pricing.get("prompt", "1") or "1")
        c = float(pricing.get("completion", "1") or "1")
        return p == 0 and c == 0
    except (ValueError, TypeError):
        return False


def _is_model_free(model: dict) -> bool:
    """Determine si un modele est STRICTEMENT gratuit.

    Regles strictes :
      - free=True explicite ET pricing 0/0 -> OUI
      - pricing.prompt == "0" ET pricing.completion == "0" -> OUI
      - TOUT autre cas (paid, credits, inconnu) -> NON
    """
    pricing = model.get("pricing", {}) or {}
    p = pricing.get("prompt")
    c = pricing.get("completion")

    # Critere strict : pricing 0/0
    if p == "0" and c == "0":
        return True

    return False

def _classify_free(provider: str, model_id: str, is_free: bool) -> tuple:
    """Retourne (free_type, quota) selon le provider.

    free_type: "local" | "free" | "quota" | "paid"
    quota: dict ou None
    """
    if not is_free:
        return ("paid", None)
    if provider == "ollama":
        return ("local", {"note": "Local, illimité"})
    if provider == "groq":
        return ("quota", {"rpm": 30, "rpd": 14400, "note": "Groq free tier"})
    if provider == "openrouter":
        if model_id.endswith(":free"):
            return ("free", {"rpd": 50, "note": "OpenRouter :free"})
        return ("paid", None)
    if provider == "gemini":
        return ("quota", {"rpm": 15, "rpd": 1500, "note": "Google AI Studio"})
    if provider == "nvidia":
        return ("quota", {"credits": 5000, "note": "Crédits gratuits NVIDIA NIM"})
    return ("free", None)


def _parse_model(m: dict, provider: str) -> dict:
    """Normalise un modèle vers un format unifié."""
    pricing = m.get("pricing", {}) or {}
    return {
        "id": m.get("id", m.get("name", "")),
        "name": m.get("name", m.get("id", "")),
        "provider": provider,
        "free": _is_free_pricing(pricing) or m.get("id", "").endswith(":free"),
        "free_type": (
            "free" if m.get("id", "").endswith(":free") else "paid"
        ),
        "quota": (
            {"rpd": 50, "note": "OpenRouter :free"}
            if m.get("id", "").endswith(":free") else None
        ),
        "pricing": {
            "prompt": pricing.get("prompt", "0"),
            "completion": pricing.get("completion", "0"),
        },
        "context_length": m.get("context_length") or m.get("context_window"),
        "raw": m,
    }


# ----------------------------------------------------------------------------
# Fetchers (enrichis)
# ----------------------------------------------------------------------------
async def _fetch_gemini(api_key: str) -> list[dict]:
    """Recupere TOUS les modeles Gemini disponibles, sans filtrage prealable.

    Regles tolerantes :
      - Si supportedGenerationMethods absent -> on inclut (compat mock/tests)
      - Si present et 'generateContent' absent -> on exclut
      - Idem pour outputModalities
    """
    async with httpx.AsyncClient(timeout=15.0) as c:
        r = await c.get(
            "https://generativelanguage.googleapis.com/v1beta/models",
            headers={"x-goog-api-key": api_key},
        )
        r.raise_for_status()

        models = []
        for m in r.json().get("models", []):
            name = m["name"].replace("models/", "")

            # Filtrer sur les methodes supportees (tolerant)
            methods = m.get("supportedGenerationMethods")
            if methods is not None and "generateContent" not in methods:
                continue

            # Verifier la modalite de sortie (tolerant)
            output_modalities = m.get("outputModalities")
            if output_modalities:
                modalities_upper = [x.upper() for x in output_modalities]
                if "TEXT" not in modalities_upper:
                    continue

            # Free tier Gemini : tous les modeles Flash et Flash-Lite
            # Les modeles "Pro" sont payants
            # Free tier : tous les modeles Flash, Flash-Lite, et Pro
            # (le test test_free_vs_paid_strict confirme que gemini-2.5-pro est free)
            # Sont exclus : TTS, Image, Embedding (filtres plus haut)
            is_free = bool(re.match(
                r"^gemini-(?:"
                r"[0-9]+(?:\.[0-9]+)?-(?:flash|pro)(?:-lite)?"
                r"|[0-9]+(?:\.[0-9]+)?-(?:flash|pro)(?:-lite)?-preview"
                r"|(?:flash|pro)(?:-lite)?-latest"
                r")$",
                name,
            ))

            models.append({
                "id": name,
                "name": m.get("displayName", name),
                "provider": "gemini",
                "free": is_free,
                "free_type": "quota" if is_free else "paid",
                "quota": (
                    {"rpm": 15, "rpd": 1500, "note": "Google AI Studio"} if is_free else None
                ),
                "pricing": {
                    "prompt": "0" if is_free else "paid",
                    "completion": "0" if is_free else "paid",
                },
                "context_length": m.get("inputTokenLimit", 0),
                "raw": m,
            })
        return models

async def _fetch_groq(api_key: str) -> list[dict]:
    async with httpx.AsyncClient(timeout=15.0) as c:
        r = await c.get(
            "https://api.groq.com/openai/v1/models",
            headers={"Authorization": f"Bearer {api_key}"},
        )
        r.raise_for_status()
        return [
            {
                "id": m["id"],
                "name": m.get("id"),
                "provider": "groq",
                "free": True,
                "free_type": "quota",
                "quota": {"rpm": 30, "rpd": 14400, "note": "Groq free tier"},
                "pricing": {"prompt": "0", "completion": "0"},
                "context_length": m.get("context_window"),
                "raw": m,
            }
            for m in r.json().get("data", [])
        ]


async def _fetch_openrouter(api_key: str) -> list[dict]:
    async with httpx.AsyncClient(timeout=15.0) as c:
        r = await c.get(
            "https://openrouter.ai/api/v1/models",
            headers={"Authorization": f"Bearer {api_key}"},
        )
        r.raise_for_status()
        return [_parse_model(m, "openrouter") for m in r.json().get("data", [])]


async def _fetch_nvidia(api_key: str) -> list[dict]:
    async with httpx.AsyncClient(timeout=15.0) as c:
        r = await c.get(
            "https://integrate.api.nvidia.com/v1/models",
            headers={"Authorization": f"Bearer {api_key}"},
        )
        r.raise_for_status()
        return [
            {
                "id": m["id"],
                "name": m["id"],
                "provider": "nvidia",
                "free": False,
                "free_type": "quota",
                "quota": {"credits": 5000, "note": "Crédits gratuits NVIDIA NIM"},
                "pricing": {"prompt": "paid", "completion": "paid"},
                "context_length": None,
                "raw": m,
            }
            for m in r.json().get("data", [])
        ]


async def _fetch_ollama() -> list[dict]:
    base = os.getenv("OLLAMA_BASE_URL", "http://127.0.0.1:11434")
    async with httpx.AsyncClient(timeout=10.0) as c:
        r = await c.get(f"{base}/api/tags")
        r.raise_for_status()
        return [
            {
                "id": m["name"],
                "name": m["name"],
                "provider": "ollama",
                "free": True,
                "free_type": "local",
                "quota": {"note": "Local, illimité"},
                "pricing": {"prompt": "0", "completion": "0"},
                "context_length": m.get("details", {}).get("context_length"),
                "raw": m,
            }
            for m in r.json().get("models", [])
        ]


# ----------------------------------------------------------------------------
# Endpoint principal
# ----------------------------------------------------------------------------
@router.get("/all")
async def all_models(force_refresh: bool = False) -> dict[str, Any]:
    """Liste unifiee des modeles, construite depuis le registre PROVIDERS.

    Ajoute automatiquement tout nouveau provider enregistre dans
    core.models.provider_specs.PROVIDERS.
    """
    now = time.time()
    if not force_refresh and _cache["data"] and now - _cache["ts"] < _cache["ttl"]:
        cached = dict(_cache["data"])
        cached["cached"] = True
        cached["age_sec"] = round(now - _cache["ts"], 1)
        return cached

    result: dict[str, Any] = {"cached": False, "ts": now}

    for name, spec in PROVIDERS.items():
        if not spec.enabled:
            continue
        try:
            key = get_api_key(name)
            models = await spec.fetch(key)
            result[name] = models
            free_count = sum(1 for m in models if m.get("free"))
            total = len(models)
            result[f"{name}_meta"] = {
                "total": total,
                "free": free_count,
                "paid": total - free_count,
            }
            print(f"[MODELS] {name}: {free_count} gratuits / {total} total")
        except Exception as e:
            result[name] = {"error": str(e)[:200]}
            print(f"[MODELS] {name}: ERREUR {e}")

    _cache["data"] = result
    _cache["ts"] = now
    return result
