from datetime import datetime, timedelta
from runtime.memory.sleep.state import CognitiveState
from runtime.core.events import EventBus

class SleepScheduler:
    """Régule les cycles de consolidation en observant l'état cognitif."""
    
    def __init__(self, event_bus: EventBus):
        self.event_bus = event_bus
        self.state = CognitiveState()
        
        self.event_bus.subscribe("EpisodeCrystallized", self._on_new_episode)
        self.event_bus.subscribe("EmotionalShock", self._on_shock)

    def _on_new_episode(self, episode_payload: dict):
        # Un nouvel épisode augmente la pression court-terme et le besoin d'abstraction long-terme
        self.state.memory_pressure = min(1.0, self.state.memory_pressure + 0.15)
        self.state.unresolved_patterns += 1
        self.evaluate()

    def _on_shock(self, payload: dict):
        self.state.emotional_load = min(1.0, self.state.emotional_load + 0.4)
        self.evaluate()

    def evaluate(self):
        """Évalue si le Runtime doit s'endormir."""
        now = __import__('datetime').datetime.now(__import__('datetime').timezone.utc)
        time_since_deep = (now - self.state.last_deep_sleep).total_seconds() / 3600 # Heures
        
        # 1. Évaluation Deep Sleep (Fatigue lourde, surcharge de patterns ou temps écoulé)
        deep_sleep_score = (
            (self.state.unresolved_patterns / 50.0) * 0.4 +
            self.state.emotional_load * 0.3 +
            min(1.0, time_since_deep / 24.0) * 0.3
        )
        
        if deep_sleep_score > 0.75 or self.state.unresolved_patterns > 100:
            self.event_bus.emit("DeepSleepTriggered", self.state)
            self.state.reset_deep()
            return # Le sommeil profond inclut le micro-sommeil

        # 2. Évaluation Micro Sleep (Nettoyage de surface)
        if self.state.memory_pressure > 0.75:
            self.event_bus.emit("MicroSleepTriggered", self.state)
            self.state.reset_micro()