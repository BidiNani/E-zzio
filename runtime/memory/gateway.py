from typing import Dict, Any, Optional
from runtime.memory.events import RuntimeEvent
from runtime.memory.sqlite.store import SQLiteEventStore

class MemoryGateway:
    """Intercepte les événements du runtime et les route vers l'EventStore selon la Policy."""

    def __init__(self, store: SQLiteEventStore, manifest_provider=None):
        self.store = store
        self.manifest_provider = manifest_provider

    def remember(self, event_payload: Dict[str, Any], retention_score: float = 1.0):
        """Enregistre un événement dans le Ledger de manière immuable."""
        success = event_payload.get("success", True)
        if not success:
            retention_score = max(retention_score, 1.0)

        event = RuntimeEvent(
            event_id=event_payload.get("request_id", "req_unknown"),
            event_type=event_payload.get("event_type", "ToolExecuted"),
            trace_id=event_payload.get("trace_id", "trace_default"),
            session_id=event_payload.get("session_id", "default_session"),
            actor=event_payload.get("actor", "kernel"),
            timestamp=event_payload.get("timestamp", "2026-07-26T00:00:00"),
            payload=event_payload
        )
        self.store.append_event(event, retention_score=retention_score)

    def _on_execution_finished(self, payload: Dict[str, Any]):
        """Callback écoutant l'événement ExecutionFinished de l'EventBus."""
        self.remember(payload)