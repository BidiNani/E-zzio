"""
E-ZZIO Core — Async Singleflight Pattern (Request Coalescing / Stampede Suppression).
Permet de fusionner N requêtes concurrentes identiques sur cache froid en un seul appel provider (Leader),
puis de diffuser le résultat déterministe à tous les appelants en attente (Waiters).

INVARIANTS :
1. STRICTEMENT TECHNIQUE : Ne modifie jamais les autorités de routage ou de mémoire.
2. SOUVERAINETÉ : 100% in-process asyncio natif, zéro dépendance externe.
3. ANTI-DEADLOCK : Protection par timeout et capture complète des exceptions du Leader.
"""
from __future__ import annotations
import asyncio
import logging
from typing import Dict, Any, Callable, Awaitable, Optional

logger = logging.getLogger("EzzioSingleflight")


class AsyncSingleflight:
    """Gestionnaire in-process de déduplication des requêtes d'inférence en vol."""

    def __init__(self):
        self._in_flight: Dict[str, asyncio.Future] = {}
        self._lock = asyncio.Lock()
        self.leader_count = 0
        self.waiter_count = 0

    async def do(
        self,
        key: str,
        coro_fn: Callable[[], Awaitable[Dict[str, Any]]],
        timeout_s: float = 60.0
    ) -> Dict[str, Any]:
        """
        Exécute coro_fn() une seule fois pour une clé donnée si plusieurs tâches concurrentes la sollicitent.
        """
        future_to_await = None
        is_leader = False

        async with self._lock:
            if key in self._in_flight:
                # Une tâche Leader exécute déjà cette requête
                future_to_await = self._in_flight[key]
                self.waiter_count += 1
                logger.info("[SINGLEFLIGHT-WAITER] Requête concurrente attachée au Leader en vol (Clé: %s...)", key[:12])
            else:
                # Première tâche : Devient le Leader
                loop = asyncio.get_running_loop()
                future_to_await = loop.create_future()
                self._in_flight[key] = future_to_await
                is_leader = True
                self.leader_count += 1
                logger.info("[SINGLEFLIGHT-LEADER] Prise de leadership pour la requête (Clé: %s...)", key[:12])

        if not is_leader:
            # Waiter : Attend le résultat du Leader
            try:
                result = await asyncio.wait_for(asyncio.shield(future_to_await), timeout=timeout_s)
                waiter_result = dict(result)
                waiter_result["singleflight_role"] = "waiter"
                return waiter_result
            except asyncio.TimeoutError:
                logger.error("[SINGLEFLIGHT-TIMEOUT] Leader bloqué pour la clé %s... -> Relâchement du Waiter", key[:12])
                return {
                    "ok": False,
                    "status": "TIMEOUT",
                    "error": f"Timeout ({timeout_s}s) en attente du résultat du Leader Singleflight",
                    "singleflight_role": "waiter_timeout"
                }
            except Exception as exc:
                logger.error("[SINGLEFLIGHT-LEADER-ERROR] Le Leader a levé une exception : %s", exc)
                return {
                    "ok": False,
                    "status": "LEADER_ERROR",
                    "error": str(exc),
                    "singleflight_role": "waiter_error"
                }

        # Leader : Exécute concrètement la fonction et notifie tous les waiters
        try:
            result = await coro_fn()
            if not future_to_await.done():
                future_to_await.set_result(result)
            
            leader_result = dict(result)
            leader_result["singleflight_role"] = "leader"
            return leader_result
        except Exception as exc:
            if not future_to_await.done():
                future_to_await.set_exception(exc)
            raise exc
        finally:
            async with self._lock:
                self._in_flight.pop(key, None)

    def get_stats(self) -> Dict[str, Any]:
        """Télémétrie du Singleflight."""
        return {
            "active_in_flight": len(self._in_flight),
            "total_leaders": self.leader_count,
            "total_waiters": self.waiter_count
        }


# Singleton global Singleflight
singleflight = AsyncSingleflight()