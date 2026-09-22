"""
E-ZZIO Core — Decoupled Signal & Event Bus (Inspiré de l'Architecture Godot).
Permet la communication asynchrone découplée entre composants (Sécurité, Télémétrie, Registre, Audit).
Chaque composant émet des signaux sans dépendre directement des abonnés.
"""
from __future__ import annotations

import asyncio
import logging
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any

logger = logging.getLogger("SignalBus")



def _now_timestamp() -> float:
    """Retourne le timestamp de la loop courante ou 0.0 si aucune loop active.

    Utilise get_running_loop() qui est safe (lève RuntimeError au lieu de
    créer implicitement une loop avec DeprecationWarning).
    """
    try:
        return asyncio.get_running_loop().time()
    except RuntimeError:
        return 0.0
@dataclass
class SignalEvent:
    name: str
    payload: dict[str, Any] = field(default_factory=dict)
    timestamp: float = field(default_factory=_now_timestamp)


class SignalBus:
    """Bus d'événements asynchrone découplé pour le noyau E-ZZIO."""

    def __init__(self):
        self._listeners: dict[str, list[Callable[[dict[str, Any]], Any]]] = {}
        self._async_listeners: dict[str, list[Callable[[dict[str, Any]], Any]]] = {}
        self._history: list[SignalEvent] = []
        self._max_history = 100

    def connect(self, signal_name: str, callback: Callable[[dict[str, Any]], Any]) -> None:
        """Abonne une fonction (synchrone ou asynchrone) à un signal."""
        if asyncio.iscoroutinefunction(callback):
            if signal_name not in self._async_listeners:
                self._async_listeners[signal_name] = []
            if callback not in self._async_listeners[signal_name]:
                self._async_listeners[signal_name].append(callback)
        else:
            if signal_name not in self._listeners:
                self._listeners[signal_name] = []
            if callback not in self._listeners[signal_name]:
                self._listeners[signal_name].append(callback)
        logger.debug("[SIGNAL-CONNECT] Listener connecté au signal '%s'", signal_name)

    def disconnect(self, signal_name: str, callback: Callable[[dict[str, Any]], Any]) -> None:
        """Désabonne un listener."""
        if signal_name in self._listeners and callback in self._listeners[signal_name]:
            self._listeners[signal_name].remove(callback)
        if signal_name in self._async_listeners and callback in self._async_listeners[signal_name]:
            self._async_listeners[signal_name].remove(callback)

    async def emit_async(self, signal_name: str, payload: dict[str, Any] | None = None) -> None:
        """Émet un signal asynchrone à tous les écouteurs enregistrés."""
        data = payload or {}
        event = SignalEvent(name=signal_name, payload=data)
        self._history.append(event)
        if len(self._history) > self._max_history:
            self._history.pop(0)

        # 1. Écouteurs synchrones
        for cb in self._listeners.get(signal_name, []):
            try:
                cb(data)
            except Exception as exc:
                logger.error("[SIGNAL-ERROR] Erreur listener synchrone '%s': %s", signal_name, exc)

        # 2. Écouteurs asynchrones
        for async_cb in self._async_listeners.get(signal_name, []):
            try:
                await async_cb(data)
            except Exception as exc:
                logger.error("[SIGNAL-ERROR] Erreur listener asynchrone '%s': %s", signal_name, exc)

    def emit(self, signal_name: str, payload: dict[str, Any] | None = None) -> None:
        """Émetteur synchrone planifiant les tâches asynchrones sans bloquer."""
        data = payload or {}
        for cb in self._listeners.get(signal_name, []):
            try:
                cb(data)
            except Exception as exc:
                logger.error("[SIGNAL-ERROR] Erreur listener synchrone '%s': %s", signal_name, exc)

        try:
            loop = asyncio.get_running_loop()
            for async_cb in self._async_listeners.get(signal_name, []):
                loop.create_task(async_cb(data))
        except RuntimeError:
            pass

    def get_event_history(self, signal_name: str | None = None) -> list[dict[str, Any]]:
        """Retourne l'historique récent des signaux émis."""
        if signal_name:
            return [{"name": e.name, "payload": e.payload} for e in self._history if e.name == signal_name]
        return [{"name": e.name, "payload": e.payload} for e in self._history]


# Singleton global
signal_bus = SignalBus()
