from enum import Enum
from dataclasses import dataclass, field
from typing import Dict, Any
import time
import uuid


class EventType(Enum):
    EXECUTION_COMPLETED = "EXECUTION_COMPLETED"
    CIRCUIT_BREAKER_TRIGGERED = "CIRCUIT_BREAKER_TRIGGERED"
    QUARANTINE_ISSUED = "QUARANTINE_ISSUED"
    SYSTEM_HEALTH_CHECK = "SYSTEM_HEALTH_CHECK"


@dataclass(frozen=True)
class TelemetryEvent:
    """Représente un événement système de télémétrie immuable."""

    event_id: str = field(default_factory=lambda: f"evt_{uuid.uuid4().hex[:8]}")
    event_type: EventType = EventType.EXECUTION_COMPLETED
    timestamp: float = field(default_factory=time.time)
    payload: Dict[str, Any] = field(default_factory=dict)
