import asyncio
import logging
import os
import socket
import time
from typing import Any

import httpx

logger = logging.getLogger("EzzioProviderHealth")

_ollama_status_cache = {"status": "OFFLINE", "timestamp": 0.0}
_CACHE_TTL_SEC = 5.0


def probe_ollama_status(host: str = "127.0.0.1", port: int = 11434, timeout_sec: float = 0.05, force_refresh: bool = False) -> str:
    """Vérifie l'état d'Ollama avec cache court (TTL 5s) et timeout strict de 50ms (décision < 1ms en cache)."""
    global _ollama_status_cache
    now = time.time()
    if not force_refresh and (now - _ollama_status_cache["timestamp"]) < _CACHE_TTL_SEC:
        return _ollama_status_cache["status"]

    try:
        with socket.create_connection((host, port), timeout=timeout_sec):
            status = "ONLINE"
    except (TimeoutError, OSError):
        status = "OFFLINE"

    _ollama_status_cache["status"] = status
    _ollama_status_cache["timestamp"] = now
    return status


def get_providers_health() -> dict[str, str]:
    """Retourne l'état de santé de chaque provider en tant qu'état de capacité."""
    return {
        "gemini": "ONLINE",
        "ollama_local": probe_ollama_status(),
    }


async def probe_ollama_detailed(ollama_url: str = "http://127.0.0.1:11434", client: Any = None) -> dict[str, Any]:
    """Sonde l'état de santé détaillé du serveur Ollama local."""
    close_client = False
    if client is None:
        client = httpx.AsyncClient()
        close_client = True
    start = time.perf_counter()
    try:
        res = await client.get(f"{ollama_url.rstrip('/')}/api/tags", timeout=3.0)
        latency_ms = int((time.perf_counter() - start) * 1000)
        if res.status_code == 200:
            models = [m.get("name") for m in res.json().get("models", [])]
            return {"online": True, "latency_ms": latency_ms, "models": models, "error": None}
        return {"online": False, "latency_ms": latency_ms, "models": [], "error": f"HTTP {res.status_code}"}
    except Exception as e:
        latency_ms = int((time.perf_counter() - start) * 1000)
        return {"online": False, "latency_ms": latency_ms, "models": [], "error": str(e)}
    finally:
        if close_client:
            await client.aclose()


async def probe_gemini_detailed(api_key: str | None = None, client: Any = None) -> dict[str, Any]:
    """Sonde la connectivité au service Gemini Cloud."""
    import httpx
    if not api_key:
        try:
            from core.config.secrets_loader import gemini_keys
            g_keys = gemini_keys()
            api_key = g_keys[0] if g_keys else os.getenv("GEMINI_API_KEY")
        except Exception:
            api_key = os.getenv("GEMINI_API_KEY")

    if not api_key:
        return {"online": False, "latency_ms": 0, "configured": False, "error": "GEMINI_API_KEY non fournie"}

    close_client = False
    if client is None:
        client = httpx.AsyncClient()
        close_client = True
    start = time.perf_counter()
    try:
        url = f"https://generativelanguage.googleapis.com/v1beta/models?key={api_key}"
        res = await client.get(url, timeout=5.0)
        latency_ms = int((time.perf_counter() - start) * 1000)
        if res.status_code == 200:
            return {"online": True, "latency_ms": latency_ms, "configured": True, "error": None}
        return {"online": False, "latency_ms": latency_ms, "configured": True, "error": f"HTTP {res.status_code}"}
    except Exception as e:
        latency_ms = int((time.perf_counter() - start) * 1000)
        return {"online": False, "latency_ms": latency_ms, "configured": True, "error": str(e)}
    finally:
        if close_client:
            await client.aclose()


async def probe_groq_detailed(client: Any = None) -> dict[str, Any]:
    """Sonde la connectivité au service Groq Cloud."""
    import httpx
    groq_key = os.getenv("GROQ_API_KEY")
    if not groq_key:
        return {"online": False, "latency_ms": 0, "configured": False, "error": "GROQ_API_KEY non fournie"}

    close_client = False
    if client is None:
        client = httpx.AsyncClient()
        close_client = True
    start = time.perf_counter()
    try:
        url = "https://api.groq.com/openai/v1/models"
        headers = {"Authorization": f"Bearer {groq_key}"}
        res = await client.get(url, headers=headers, timeout=5.0)
        latency_ms = int((time.perf_counter() - start) * 1000)
        if res.status_code == 200:
            models = [m.get("id") for m in res.json().get("data", [])]
            return {"online": True, "latency_ms": latency_ms, "configured": True, "models": models, "error": None}
        return {"online": False, "latency_ms": latency_ms, "configured": True, "error": f"HTTP {res.status_code}"}
    except Exception as e:
        latency_ms = int((time.perf_counter() - start) * 1000)
        return {"online": False, "latency_ms": latency_ms, "configured": True, "error": str(e)}
    finally:
        if close_client:
            await client.aclose()


def probe_antigravity_detailed() -> dict[str, Any]:
    """Inspecte le statut du provider Antigravity."""
    return {
        "online": False,
        "status": "BLOCKED_BY_EXTERNAL_QUOTA",
        "latency_ms": 0,
        "quota": "EXHAUSTED",
        "fail_safe": True,
        "error": "Antigravity = BLOCKED_BY_EXTERNAL_QUOTA",
    }


async def get_full_providers_health(
    ollama_url: str = "http://127.0.0.1:11434",
    gemini_api_key: str | None = None,
    client: Any = None,
) -> dict[str, Any]:
    """Fournit une synthèse complète de la santé de tous les providers configurés."""
    results = await asyncio.gather(
        probe_ollama_detailed(ollama_url=ollama_url, client=client),
        probe_gemini_detailed(api_key=gemini_api_key, client=client),
        probe_groq_detailed(client=client),
        return_exceptions=True,
    )
    ollama_health = results[0] if not isinstance(results[0], Exception) else {"online": False, "error": str(results[0])}
    gemini_health = results[1] if not isinstance(results[1], Exception) else {"online": False, "error": str(results[1])}
    groq_health = results[2] if not isinstance(results[2], Exception) else {"online": False, "error": str(results[2])}
    antigravity_health = probe_antigravity_detailed()
    return {
        "timestamp": time.time(),
        "providers": {
            "ollama": ollama_health,
            "gemini": gemini_health,
            "groq": groq_health,
            "antigravity": antigravity_health,
        },
        "primary_available": bool(ollama_health.get("online") or gemini_health.get("online") or groq_health.get("online")),
        "deterministic_support": {
            "ollama": "DETERMINISTIC",
            "gemini": "BEST_EFFORT_DETERMINISTIC",
            "groq": "BEST_EFFORT_DETERMINISTIC",
            "antigravity": "UNSUPPORTED",
        },
    }
