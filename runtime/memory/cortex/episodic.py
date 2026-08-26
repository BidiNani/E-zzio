import uuid
import threading
from collections import defaultdict
from runtime.core.events import EventBus
from runtime.memory.sqlite.store import SQLiteEventStore
from runtime.memory.events import RuntimeEvent


class EpisodicCortex:
    """Écoute le flux d'événements et construit des Unités de Vie (Épisodes)."""

    def __init__(self, event_bus: EventBus, store: SQLiteEventStore):
        self.store = store
        self.event_bus = event_bus
        self.active_episodes = defaultdict(list)
        self._lock = threading.Lock()

        # Le Cortex écoute les événements mémorisés (après le filtre de saillance)
        self.event_bus.subscribe("MemoryEventAppended", self._on_memory_event)

    def _on_memory_event(self, payload: dict):
        # Payload contient event (RuntimeEvent) et score (float)
        event: RuntimeEvent = payload["event"]
        score: float = payload["score"]

        # Oubli biologique : Si la saillance est trop faible, l'événement ne forme pas de souvenir épisodique
        if score < 0.2:
            return

        with self._lock:
            self.active_episodes[event.session_id].append(event)

            # Flush basique : On fige un épisode chaque fois qu'une action se termine (pour l'instant)
            # En Phase 7.5, le flush pourrait être déclenché par un changement de contexte agentique.
            if event.event_type == "ToolExecuted":
                self._crystallize_episode(event.session_id)

    def _crystallize_episode(self, session_id: str):
        events = self.active_episodes.pop(session_id, [])
        if not events:
            return

        # Agrégation des signaux pour définir l'importance de l'épisode
        started_at = events[0].timestamp
        ended_at = events[-1].timestamp

        # Extraction du contexte depuis le dernier ToolExecuted
        last_evt = events[-1]
        success = last_evt.payload.get("execution", {}).get("success", True)

        action_name = last_evt.payload.get("capability", {}).get("tool", "unknown_action")
        outcome = "Action réussie" if success else f"Échec: {last_evt.payload.get('execution', {}).get('error', 'unknown')}"

        episode = {
            "episode_id": f"ep_{uuid.uuid4().hex[:12]}",
            "session_id": session_id,
            "started_at": started_at,
            "ended_at": ended_at,
            "context": {"environment": "E-zzio Runtime", "action_attempted": action_name},
            "intent": f"Exécuter {action_name}",
            "events": [e.event_id for e in events],  # Référence temporelle (ADN)
            "outcome": outcome,
            "success": success,
            "importance": 0.8 if not success else 0.5,  # Moyenne de l'importance des événements
            "confidence": 1.0,
            "created_from_event": last_evt.event_id,
        }

        self.store.save_episode(episode)
        # Émet l'épisode cristallisé pour le futur Semantic Cortex (Pattern Detector)
        self.event_bus.emit("EpisodeCrystallized", episode)
