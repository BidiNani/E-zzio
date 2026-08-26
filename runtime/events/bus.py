from __future__ import annotations
import logging
import threading
import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Callable

logger = logging.getLogger("ezzio.event_bus")


@dataclass(frozen=True, slots=True)
class Event:
    """Événement immuable du Runtime E-ZZIO."""

    type: str
    actor: str
    source: str
    payload: dict[str, Any]
    security_context: str = "SYSTEM_DEFAULT"
    correlation_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    timestamp: float = field(default_factory=time.time)


class EzzioEventBus:
    """
    Event Bus V4 Foundation.
    Garanties : événements immuables, historique borné, thread-safe, isolation des erreurs.
    """

    def __init__(self, max_history: int = 1000):
        if max_history < 1:
            raise ValueError("max_history doit être >= 1")

        self._lock = threading.RLock()
        self._subscribers: dict[str, list[Callable[[Event], None]]] = {}
        self._recent_events: list[Event] = []
        self._max_history = max_history

    def subscribe(self, event_type: str, callback: Callable[[Event], None]) -> None:
        if not event_type:
            raise ValueError("event_type obligatoire")
        if not callable(callback):
            raise TypeError("callback doit être callable")

        with self._lock:
            self._subscribers.setdefault(event_type, []).append(callback)

    def publish(self, event: Event) -> None:
        if not isinstance(event, Event):
            raise TypeError("publish() attend un Event")

        with self._lock:
            self._recent_events.append(event)
            if len(self._recent_events) > self._max_history:
                del self._recent_events[: len(self._recent_events) - self._max_history]

            # Copie pour éviter un blocage si un subscriber se désinscrit pendant l'itération
            subscribers = tuple(self._subscribers.get(event.type, ()))

        for callback in subscribers:
            try:
                callback(event)
            except Exception:
                logger.exception("Subscriber failed for event=%s subscriber=%r", event.type, callback)

    def recent_events(self) -> tuple[Event, ...]:
        with self._lock:
            return tuple(self._recent_events)


kernel_bus = EzzioEventBus()
