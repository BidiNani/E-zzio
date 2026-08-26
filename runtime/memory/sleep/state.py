from dataclasses import dataclass, field
from datetime import datetime


@dataclass
class CognitiveState:
    """Représente la fatigue et la charge métabolique pure du Runtime (Corrigé: field factory)."""

    memory_pressure: float = 0.0
    unresolved_patterns: int = 0
    last_micro_sleep: datetime = field(default_factory=lambda: __import__("datetime").datetime.now(__import__("datetime").timezone.utc))
    last_deep_sleep: datetime = field(default_factory=lambda: __import__("datetime").datetime.now(__import__("datetime").timezone.utc))

    def reset_micro(self):
        self.memory_pressure = 0.0
        self.last_micro_sleep = __import__("datetime").datetime.now(__import__("datetime").timezone.utc)

    def reset_deep(self):
        self.unresolved_patterns = 0
        self.last_deep_sleep = __import__("datetime").datetime.now(__import__("datetime").timezone.utc)
