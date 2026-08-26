import threading
import json
import time
from runtime.core.events import EventBus
from runtime.memory.sqlite.store import SQLiteEventStore

SAFE_FIELDS = ["episode_id", "outcome", "intent", "context"]


class DreamEngine:
    """Producteur unique de l'événement de clôture avec un contrat de données versionné (v1.0)."""

    def __init__(self, event_bus: EventBus, store: SQLiteEventStore):
        self.event_bus = event_bus
        self.store = store
        self.event_bus.subscribe("DreamModeTriggered", self._start_dreaming)
        self.event_bus.subscribe("ExecutionFinished", self._on_execution_finished)

    def _start_dreaming(self, payload: dict):
        self.event_bus.emit("AuditLog", {"message": "DreamEngine : Signal DreamModeTriggered reçu.", "level": "INFO"})
        threading.Thread(target=self._dream_worker, args=(payload,), daemon=True).start()

    def _dream_worker(self, payload: dict):
        episodes = payload.get("episodes", [])
        episode_ids = payload.get("episode_ids", [])
        if not episodes:
            return

        sanitized_episodes = [{k: ep[k] for k in SAFE_FIELDS if k in ep} for ep in episodes]
        self.event_bus.emit("AuditLog", {"message": f"DreamEngine : Rêve initié sur {len(sanitized_episodes)} épisodes.", "level": "INFO"})

        request_payload = {
            "tool_name": "llm.cognitive_reflection",
            "arguments": {"episodes_data": sanitized_episodes},
            "context_metadata": {"origin": "dream_engine", "episode_ids": episode_ids},
        }
        self.event_bus.emit("SystemActionRequested", request_payload)

    def _on_execution_finished(self, payload: dict):
        request_id = payload.get("request_id", "")
        if not request_id.startswith("sys_dream_"):
            return

        if not payload.get("success", False):
            return

        metadata = payload.get("metadata", {})
        output = payload.get("output", "[]")

        try:
            proposals = json.loads(output)
            if isinstance(proposals, list) and proposals:
                # Contrat v1.0 pour les propositions générées
                proposal_envelope = {
                    "event": "ReflectionProposalGenerated",
                    "version": "1.0",
                    "source": "DreamEngine",
                    "timestamp": int(time.time()),
                    "proposals": proposals,
                }
                self.event_bus.emit("ReflectionProposalGenerated", proposal_envelope)

                episode_ids = metadata.get("episode_ids", [])
                if episode_ids:
                    # Contrat v1.0 strict pour l'unicité de la clôture biologique
                    consolidation_envelope = {
                        "event": "EpisodesConsolidated",
                        "version": "1.0",
                        "source": "DreamEngine",
                        "timestamp": int(time.time()),
                        "episode_ids": episode_ids,
                    }
                    self.event_bus.emit("EpisodesConsolidated", consolidation_envelope)
        except Exception as e:
            self.event_bus.emit("AuditLog", {"message": f"DreamEngine Error parsing output: {e}", "level": "ERROR"})
