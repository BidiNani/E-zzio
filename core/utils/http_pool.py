"""
E-ZZIO Utilities — High-Performance Async HTTP Connection Pool.
Optimise les échanges réseau avec réutilisation des connexions TCP/SSL (Keep-Alive) :
- Évite la surcharge de renégociation TLS à chaque requête
- Gère le pool global avec limites de concurrence et timeouts optimisés
- Nettoyage propre au shutdown
"""
from __future__ import annotations
import httpx
from typing import Optional

_global_async_client: Optional[httpx.AsyncClient] = None


def get_http_client(timeout: float = 10.0) -> httpx.AsyncClient:
    """Retourne une instance singleton de client HTTP asynchrone avec pool de connexions optimisé."""
    global _global_async_client
    if _global_async_client is None or _global_async_client.is_closed:
        limits = httpx.Limits(
            max_keepalive_connections=20,
            max_connections=50,
            keepalive_expiry=30.0
        )
        _global_async_client = httpx.AsyncClient(
            limits=limits,
            timeout=httpx.Timeout(timeout, connect=5.0),
            follow_redirects=True,
            http2=False
        )
    return _global_async_client


async def close_http_client():
    """Ferme proprement le pool de connexions HTTP global."""
    global _global_async_client
    if _global_async_client is not None and not _global_async_client.is_closed:
        await _global_async_client.aclose()
        _global_async_client = None
