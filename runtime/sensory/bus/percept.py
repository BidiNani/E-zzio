"""
E-ZZIO V9 — Universal Percept Schema
Définit l'unité d'information sensorielle standardisée.
"""

from datetime import datetime, timezone
from typing import Any, Dict
import uuid


class Percept:
    def __init__(self, source: str, data: Dict[str, Any], priority: str = "LOW"):
        self.percept_id = f"PERC-{uuid.uuid4().hex[:8].upper()}"
        self.timestamp = datetime.now(timezone.utc).isoformat()
        self.source = source
        self.priority = priority
        self.data = data

    def to_dict(self) -> Dict[str, Any]:
        return {
            "percept_id": self.percept_id,
            "timestamp": self.timestamp,
            "source": self.source,
            "priority": self.priority,
            "data": self.data,
        }
