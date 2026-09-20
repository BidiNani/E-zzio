"""
E-ZZIO — Fetch HTTP des providers cloud.

RÔLE : fonctions techniques (fetch, is_free, check) pour interroger
les APIs HTTP des providers. Le CATALOGUE des modèles est dans
core/routing/registry.py — ce fichier ne fait que le fetching.

Ajouter un NOUVEAU provider :
  1. Definir _xxx_is_free, _xxx_fetch, _xxx_check
  2. Enregistrer une ProviderSpec dans PROVIDERS
  3. C'est tout.
"""
from __future__ import annotations

import os
import re
from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field

import httpx

FetchFn = Callable[[str], Awaitable[list[dict]]]
FreeFn = Callable[[str], bool]
CheckFn = Callable[[str, str], Awaitable[dict]]


@dataclass
class ProviderSpec:
    name: str
    fetch: FetchFn
    is_free: FreeFn
    check: CheckFn
    free_note: str = ""
    default_quota: dict | None = None
    enabled: bool = True
    metadata: dict = field(default_factory=dict)


def _gemini_key() -> str:
    try:
        from core.config.secrets_loader import gemini_keys
        keys = gemini_keys()
        return keys[0] if keys else ""
    except Exception:
        return ""


async def _http_get_json(url: str, headers: dict | None = None, timeout: float = 15.0) -> dict:
    async with httpx.AsyncClient(timeout=timeout) as c:
        r = await c.get(url, headers=headers or {})
        r.raise_for_status()
        return r.json()


# ============================================================
# GEMINI
# ============================================================

# Regle metier (confirmee par tests unitaires) :
#   GRATUIT : gemini-X.Y-flash, gemini-X.Y-flash-lite, gemini-X.Y-pro
#   PAYANT  : gemma-*, gemini-*-tts, gemini-*-image
_GEMINI_FREE_RE = re.compile(
    r"^gemini-(?:"
    r"[0-9]+(?:\.[0-9]+)?-(?:flash|pro)(?:-lite)?"
    r"|[0-9]+(?:\.[0-9]+)?-(?:flash|pro)(?:-lite)?-preview"
    r"|(?:flash|pro)(?:-lite)?-latest"
    r")$"
)


def _gemini_is_free(model_id: str) -> bool:
    return bool(_GEMINI_FREE_RE.match(model_id))


async def _gemini_fetch(api_key: str) -> list[dict]:
    data = await _http_get_json(
        "https://generativelanguage.googleapis.com/v1beta/models",
        headers={"x-goog-api-key": api_key},
    )
    out: list[dict] = []
    for m in data.get("models", []):
        name = m["name"].replace("models/", "")
        methods = m.get("supportedGenerationMethods")
        if methods is not None and "generateContent" not in methods:
            continue
        mods = m.get("outputModalities")
        if mods and "TEXT" not in [x.upper() for x in mods]:
            continue
        free = _gemini_is_free(name)
        out.append({
            "id": name,
            "name": m.get("displayName", name),
            "provider": "gemini",
            "free": free,
            "free_type": "quota" if free else "paid",
            "quota": {"rpm": 15, "rpd": 1500, "note": "Google AI Studio"} if free else None,
            "pricing": {"prompt": "0" if free else "paid", "completion": "0" if free else "paid"},
            "context_length": m.get("inputTokenLimit", 0),
            "raw": m,
        })
    return out


async def _gemini_check(api_key: str, model_id: str) -> dict:
    try:
        async with httpx.AsyncClient(timeout=15.0) as c:
            url = f"https://generativelanguage.googleapis.com/v1beta/models/{model_id}"
            r = await c.get(url, headers={"x-goog-api-key": api_key})
            if r.status_code == 404:
                return {"status": "unavailable", "error": "model_not_found"}
            if r.status_code == 429:
                return {"status": "unavailable", "error": "rate_limit"}
            if r.status_code != 200:
                return {"status": "unavailable", "error": f"HTTP {r.status_code}"}
            meta = r.json()
            methods = meta.get("supportedGenerationMethods", [])
            if "generateContent" not in methods:
                return {"status": "unavailable", "error": "non_chat_model"}
            mods = meta.get("outputModalities") or meta.get("output_modalities")
            if mods and "TEXT" not in [x.upper() for x in mods]:
                return {"status": "unavailable", "error": "non_text_output"}
            return {"status": "available", "error": None}
    except httpx.TimeoutException:
        return {"status": "unknown", "error": "timeout"}
    except Exception as e:
        return {"status": "unknown", "error": str(e)[:100]}


# ============================================================
# OPENROUTER
# ============================================================

def _openrouter_is_free(model_id: str) -> bool:
    return model_id.endswith(":free")


async def _openrouter_fetch(api_key: str) -> list[dict]:
    data = await _http_get_json(
        "https://openrouter.ai/api/v1/models",
        headers={"Authorization": f"Bearer {api_key}"},
    )
    out: list[dict] = []
    for m in data.get("data", []):
        model_id = m.get("id", "")
        pr = m.get("pricing", {}) or {}
        is_free_suffix = _openrouter_is_free(model_id)
        free = (pr.get("prompt") == "0" and pr.get("completion") == "0") or is_free_suffix
        out.append({
            "id": model_id,
            "name": m.get("name", model_id),
            "provider": "openrouter",
            "free": free,
            "free_type": "free" if is_free_suffix else ("quota" if free else "paid"),
            "quota": {"rpd": 50, "note": "OpenRouter :free"} if is_free_suffix else None,
            "pricing": {"prompt": pr.get("prompt", "0"), "completion": pr.get("completion", "0")},
            "context_length": m.get("context_length"),
            "raw": m,
        })
    return out


async def _openrouter_check(api_key: str, model_id: str) -> dict:
    try:
        async with httpx.AsyncClient(timeout=15.0) as c:
            body = {"model": model_id, "messages": [{"role": "user", "content": "hi"}], "max_tokens": 1}
            r = await c.post(
                "https://openrouter.ai/api/v1/chat/completions",
                headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
                json=body,
            )
            if r.status_code == 200:
                d = r.json()
                ch = d.get("choices", [])
                if ch and ch[0].get("message", {}).get("content"):
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


# ============================================================
# GROQ
# ============================================================

def _groq_is_free(_model_id: str) -> bool:
    return True


async def _groq_fetch(api_key: str) -> list[dict]:
    data = await _http_get_json(
        "https://api.groq.com/openai/v1/models",
        headers={"Authorization": f"Bearer {api_key}"},
    )
    out: list[dict] = []
    for m in data.get("data", []):
        model_id = m.get("id", "")
        out.append({
            "id": model_id,
            "name": model_id,
            "provider": "groq",
            "free": True,
            "free_type": "quota",
            "quota": {"rpm": 30, "rpd": 14400, "note": "Groq free tier"},
            "pricing": {"prompt": "0", "completion": "0"},
            "context_length": m.get("context_window"),
            "raw": m,
        })
    return out


async def _groq_check(api_key: str, model_id: str) -> dict:
    try:
        async with httpx.AsyncClient(timeout=15.0) as c:
            body = {"model": model_id, "messages": [{"role": "user", "content": "hi"}], "max_tokens": 1}
            r = await c.post(
                "https://api.groq.com/openai/v1/chat/completions",
                headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
                json=body,
            )
            if r.status_code == 200:
                d = r.json()
                ch = d.get("choices", [])
                if ch and ch[0].get("message", {}).get("content"):
                    return {"status": "available", "error": None}
                return {"status": "unavailable", "error": "empty_response"}
            if r.status_code == 429:
                return {"status": "unavailable", "error": "rate_limit"}
            if r.status_code == 404:
                return {"status": "unavailable", "error": "model_not_found"}
            return {"status": "unavailable", "error": f"HTTP {r.status_code}"}
    except httpx.TimeoutException:
        return {"status": "unknown", "error": "timeout"}
    except Exception as e:
        return {"status": "unknown", "error": str(e)[:100]}


# ============================================================
# NVIDIA NIM
# ============================================================

def _nvidia_is_free(_model_id: str) -> bool:
    return True


async def _nvidia_fetch(api_key: str) -> list[dict]:
    data = await _http_get_json(
        "https://integrate.api.nvidia.com/v1/models",
        headers={"Authorization": f"Bearer {api_key}"},
    )
    out: list[dict] = []
    for m in data.get("data", []):
        model_id = m.get("id", "")
        out.append({
            "id": model_id,
            "name": model_id,
            "provider": "nvidia",
            "free": True,
            "free_type": "quota",
            "quota": {"credits": 5000, "note": "Credits gratuits NVIDIA NIM"},
            "pricing": {"prompt": "0", "completion": "0"},
            "context_length": None,
            "raw": m,
        })
    return out


async def _nvidia_check(api_key: str, model_id: str) -> dict:
    try:
        async with httpx.AsyncClient(timeout=15.0) as c:
            body = {"model": model_id, "messages": [{"role": "user", "content": "hi"}], "max_tokens": 1}
            r = await c.post(
                "https://integrate.api.nvidia.com/v1/chat/completions",
                headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
                json=body,
            )
            if r.status_code == 200:
                d = r.json()
                ch = d.get("choices", [])
                if ch and ch[0].get("message", {}).get("content"):
                    return {"status": "available", "error": None}
                return {"status": "unavailable", "error": "empty_response"}
            if r.status_code == 429:
                return {"status": "unavailable", "error": "rate_limit"}
            if r.status_code == 404:
                return {"status": "unavailable", "error": "model_not_found"}
            return {"status": "unavailable", "error": f"HTTP {r.status_code}"}
    except httpx.TimeoutException:
        return {"status": "unknown", "error": "timeout"}
    except Exception as e:
        return {"status": "unknown", "error": str(e)[:100]}


# ============================================================
# OLLAMA
# ============================================================

def _ollama_is_free(_model_id: str) -> bool:
    return True


async def _ollama_fetch(_api_key: str) -> list[dict]:
    base = os.getenv("OLLAMA_BASE_URL", "http://127.0.0.1:11434")
    data = await _http_get_json(f"{base}/api/tags", timeout=10.0)
    out: list[dict] = []
    for m in data.get("models", []):
        name = m.get("name", "")
        out.append({
            "id": name,
            "name": name,
            "provider": "ollama",
            "free": True,
            "free_type": "local",
            "quota": {"note": "Local, illimite"},
            "pricing": {"prompt": "0", "completion": "0"},
            "context_length": m.get("details", {}).get("context_length"),
            "raw": m,
        })
    return out


async def _ollama_check(_api_key: str, model_id: str) -> dict:
    base = os.getenv("OLLAMA_BASE_URL", "http://127.0.0.1:11434")
    try:
        async with httpx.AsyncClient(timeout=15.0) as c:
            r = await c.post(f"{base}/api/generate", json={"model": model_id, "prompt": "", "stream": False})
            if r.status_code == 200:
                return {"status": "available", "error": None}
            return {"status": "unavailable", "error": f"HTTP {r.status_code}"}
    except httpx.TimeoutException:
        return {"status": "unknown", "error": "timeout"}
    except Exception as e:
        return {"status": "unknown", "error": str(e)[:100]}


# ============================================================
# REGISTRE
# ============================================================

PROVIDERS: dict[str, ProviderSpec] = {
    "gemini": ProviderSpec(
        name="gemini",
        fetch=_gemini_fetch,
        is_free=_gemini_is_free,
        check=_gemini_check,
        free_note="Google AI Studio",
        default_quota={"rpm": 15, "rpd": 1500, "note": "Google AI Studio"},
    ),
    "openrouter": ProviderSpec(
        name="openrouter",
        fetch=_openrouter_fetch,
        is_free=_openrouter_is_free,
        check=_openrouter_check,
        free_note="OpenRouter :free",
    ),
    "groq": ProviderSpec(
        name="groq",
        fetch=_groq_fetch,
        is_free=_groq_is_free,
        check=_groq_check,
        free_note="Groq free tier",
        default_quota={"rpm": 30, "rpd": 14400, "note": "Groq free tier"},
    ),
    "nvidia": ProviderSpec(
        name="nvidia",
        fetch=_nvidia_fetch,
        is_free=_nvidia_is_free,
        check=_nvidia_check,
        free_note="NVIDIA NIM credits",
        default_quota={"credits": 5000, "note": "Credits gratuits NVIDIA NIM"},
    ),
    "ollama": ProviderSpec(
        name="ollama",
        fetch=_ollama_fetch,
        is_free=_ollama_is_free,
        check=_ollama_check,
        free_note="Local, illimite",
        default_quota={"note": "Local, illimite"},
    ),
}


def get_provider(name: str) -> ProviderSpec | None:
    return PROVIDERS.get(name)


def get_enabled_providers() -> list[str]:
    return [n for n, s in PROVIDERS.items() if s.enabled]


def get_api_key(provider: str) -> str:
    if provider == "gemini":
        return _gemini_key()
    env_map = {
        "openrouter": "OPENROUTER_API_KEY",
        "groq": "GROQ_API_KEY",
        "nvidia": "NVIDIA_API_KEY",
        "ollama": "",
    }
    env_var = env_map.get(provider, f"{provider.upper()}_API_KEY")
    return os.getenv(env_var, "") if env_var else ""
