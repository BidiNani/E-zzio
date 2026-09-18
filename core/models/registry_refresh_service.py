"""
E-ZZIO — core/models/registry_refresh_service.py
==================================================
Service de synchronisation automatique du registre Gemini.

Expose trois déclencheurs :
  1. startup()       — appelé une fois au démarrage d'E-ZzIO
  2. trigger()       — déclenché manuellement (route POST /api/models/registry/refresh/gemini)
  3. _scheduler_loop() — tâche asyncio interne, 1 refresh / 24h

INVARIANTS ABSOLUS :
  - ModelRouter non modifié
  - gemini_pool.py non modifié
  - Aucune activation automatique
  - Aucun secret dans les logs ou réponses
  - Fail-safe : échec du refresh → WARNING, E-ZzIO continue
  - 1 seul refresh actif à la fois (asyncio.Lock)
"""
from __future__ import annotations

import asyncio
import logging
import time
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

logger = logging.getLogger("EzzioRegistryRefreshService")

# ── Intervalle du scheduler ──────────────────────────────────────────────────
_SCHEDULER_INTERVAL_SECONDS: float = 86_400.0  # 24 heures


@dataclass
class RefreshStats:
    """Compteurs observabilité — jamais de secret."""
    total: int = 0
    success: int = 0
    failure: int = 0
    last_success_iso: str | None = None
    last_failure_iso: str | None = None
    last_discovered: int = 0
    last_new: int = 0
    last_superseded: int = 0


class GeminiRegistryRefreshService:
    """
    Service singleton pour la synchronisation automatique du registre Gemini.

    Usage :
        service = GeminiRegistryRefreshService()
        await service.startup()           # au démarrage
        result = await service.trigger()  # déclenchement manuel
        # Le scheduler démarre automatiquement dans startup()
    """

    def __init__(self, scheduler_interval: float = _SCHEDULER_INTERVAL_SECONDS) -> None:
        self._lock = asyncio.Lock()
        self._stats = RefreshStats()
        self._scheduler_task: asyncio.Task | None = None
        self._scheduler_interval = scheduler_interval
        self._started = False

    # ── API publique ─────────────────────────────────────────────────────────

    async def startup(self) -> dict[str, Any]:
        """
        Appelé au démarrage d'E-ZzIO.

        CRITIQUE : toute exception de la Gemini API est interceptée.
        La failure n'empêche JAMAIS le démarrage de l'application.

        Lance également le scheduler quotidien en arrière-plan.
        """
        logger.info("[REGISTRY-SERVICE] Démarrage : refresh Gemini au boot.")
        result: dict[str, Any] = {"startup": True, "status": "unknown"}

        try:
            result = await self._do_refresh(trigger="startup")
        except Exception as exc:
            # Fail-safe absolu — startup ne plante jamais
            logger.warning(
                "[REGISTRY-SERVICE] Refresh démarrage ÉCHEC (non-bloquant). "
                "E-ZzIO continue. Cause : %s : %s",
                type(exc).__name__,
                exc,
            )
            result = {
                "startup": True,
                "status": "failure",
                "error": type(exc).__name__,
                # NE PAS inclure le message complet de l'exception
                # (peut contenir des informations de réseau/auth)
            }

        # Lancer le scheduler quotidien une seule fois
        if not self._started:
            self._started = True
            self._scheduler_task = asyncio.create_task(
                self._scheduler_loop(), name="gemini_registry_daily_scheduler"
            )
            logger.info(
                "[REGISTRY-SERVICE] Scheduler quotidien démarré "
                "(intervalle = %.0fs).",
                self._scheduler_interval,
            )

        return result

    async def trigger(self) -> dict[str, Any]:
        """
        Déclenchement manuel du refresh.
        Retourne immédiatement si un refresh est déjà en cours.
        """
        if self._lock.locked():
            logger.info("[REGISTRY-SERVICE] Refresh ignoré : un refresh est déjà en cours.")
            return {
                "status": "skipped",
                "reason": "refresh_already_running",
                "stats": self._safe_stats(),
            }
        return await self._do_refresh(trigger="manual")

    async def shutdown(self) -> None:
        """Annule proprement le scheduler lors de l'arrêt de l'application."""
        if self._scheduler_task and not self._scheduler_task.done():
            self._scheduler_task.cancel()
            try:
                await self._scheduler_task
            except asyncio.CancelledError:
                pass
            logger.info("[REGISTRY-SERVICE] Scheduler arrêté proprement.")

    def stats(self) -> dict[str, Any]:
        """Retourne les statistiques actuelles (aucun secret)."""
        return self._safe_stats()

    # ── Implémentation interne ───────────────────────────────────────────────

    async def _do_refresh(self, *, trigger: str) -> dict[str, Any]:
        """
        Exécute refresh_gemini_registry_async() avec protection de concurrence.

        Lève l'exception originale en cas d'échec (le caller gère le fail-safe
        selon son contexte : startup vs manual).
        """
        async with self._lock:
            logger.info(
                "[REGISTRY-SERVICE] Refresh Gemini démarré (trigger=%s).", trigger
            )
            self._stats.total += 1
            t0 = time.perf_counter()

            # Import local — évite les cycles d'import au niveau module
            # et garantit que load_secrets() a déjà été appelé par web_server
            from core.models.registry_refresh import refresh_gemini_registry_async

            try:
                result = await refresh_gemini_registry_async()
            except Exception as exc:
                self._stats.failure += 1
                self._stats.last_failure_iso = datetime.now(UTC).isoformat()
                logger.warning(
                    "[REGISTRY-SERVICE] Refresh ÉCHEC (trigger=%s) : %s : %s",
                    trigger,
                    type(exc).__name__,
                    exc,
                )
                raise  # propagé au caller pour fail-safe spécifique au contexte

            elapsed = time.perf_counter() - t0
            self._stats.success += 1
            self._stats.last_success_iso = datetime.now(UTC).isoformat()
            self._stats.last_discovered = result.get("discovered_count", 0)
            self._stats.last_new = len(result.get("new_models", []))
            self._stats.last_superseded = len(result.get("superseded_models", []))

            logger.info(
                "[REGISTRY-SERVICE] Refresh SUCCÈS (trigger=%s) en %.2fs — "
                "discovered=%d, new=%d, superseded=%d.",
                trigger,
                elapsed,
                self._stats.last_discovered,
                self._stats.last_new,
                self._stats.last_superseded,
            )

            return {
                "status": "success",
                "trigger": trigger,
                "duration_seconds": round(elapsed, 3),
                "provider": "gemini",
                "discovered_count": self._stats.last_discovered,
                "new_count": self._stats.last_new,
                "superseded_count": self._stats.last_superseded,
                "registry_count": result.get("registry_count_after", 0),
                "timestamp": self._stats.last_success_iso,
                "stats": self._safe_stats(),
            }

    async def _scheduler_loop(self) -> None:
        """
        Boucle asyncio quotidienne.

        Une exception dans un refresh ne tue pas la boucle.
        Le scheduler survit indépendamment des résultats individuels.
        """
        logger.info(
            "[REGISTRY-SERVICE] Scheduler : premier refresh dans %.0f secondes.",
            self._scheduler_interval,
        )
        await asyncio.sleep(self._scheduler_interval)

        while True:
            logger.info("[REGISTRY-SERVICE] Scheduler : tick quotidien.")
            try:
                if self._lock.locked():
                    logger.info(
                        "[REGISTRY-SERVICE] Scheduler : refresh ignoré, "
                        "un refresh est déjà en cours."
                    )
                else:
                    await self._do_refresh(trigger="scheduler")
            except asyncio.CancelledError:
                logger.info("[REGISTRY-SERVICE] Scheduler : annulé proprement.")
                return
            except Exception as exc:
                # Fail-safe : le scheduler survit à toute exception
                logger.warning(
                    "[REGISTRY-SERVICE] Scheduler : refresh ÉCHEC (non-bloquant). "
                    "Prochain tick dans %.0fs. Cause : %s : %s",
                    self._scheduler_interval,
                    type(exc).__name__,
                    exc,
                )

            try:
                await asyncio.sleep(self._scheduler_interval)
            except asyncio.CancelledError:
                logger.info("[REGISTRY-SERVICE] Scheduler : annulé pendant le sleep.")
                return

    def _safe_stats(self) -> dict[str, Any]:
        """Sérialise les stats sans aucun secret."""
        return {
            "gemini_registry_refresh_total": self._stats.total,
            "gemini_registry_refresh_success": self._stats.success,
            "gemini_registry_refresh_failure": self._stats.failure,
            "gemini_registry_models_discovered": self._stats.last_discovered,
            "gemini_registry_models_new": self._stats.last_new,
            "gemini_registry_models_superseded": self._stats.last_superseded,
            "last_success": self._stats.last_success_iso,
            "last_failure": self._stats.last_failure_iso,
        }


# ── Singleton applicatif ─────────────────────────────────────────────────────
# Instancié ici ; web_server.py y accède directement.
gemini_registry_service = GeminiRegistryRefreshService()
