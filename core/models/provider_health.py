import logging
import socket
import time

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
