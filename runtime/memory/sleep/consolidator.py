import threading
import sqlite3
from runtime.core.events import EventBus
from runtime.memory.sqlite.store import SQLiteEventStore

class Consolidator:
    """Consommateur pur : Marque les épisodes en base à la réception de l'enveloppe validée."""
    def __init__(self, event_bus: EventBus, store: SQLiteEventStore):
        self.event_bus = event_bus
        self.store = store
        self.event_bus.subscribe("MicroSleepTriggered", self._trigger_micro)
        self.event_bus.subscribe("DeepSleepTriggered", self._trigger_deep)
        self.event_bus.subscribe("EpisodesConsolidated", self.mark_consolidated)

    def _trigger_micro(self, state):
        threading.Thread(target=self._micro_sleep_worker, args=(state,), daemon=True).start()

    def _trigger_deep(self, state):
        threading.Thread(target=self._deep_sleep_worker, args=(state,), daemon=True).start()

    def _micro_sleep_worker(self, state):
        self.event_bus.emit("AuditLog", {"message": "Micro Sleep achevé.", "level": "INFO"})

    def _deep_sleep_worker(self, state):
        with sqlite3.connect(self.store.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute("SELECT * FROM episodes WHERE consolidated = 0 LIMIT 10")
            unresolved = [dict(r) for r in cursor.fetchall()]

        if not unresolved: return

        episode_ids = [ep["episode_id"] for ep in unresolved]
        self.event_bus.emit("AuditLog", {"message": f"Deep Sleep : {len(episode_ids)} épisodes extraits.", "level": "INFO"})
        
        self.event_bus.emit("DreamModeTriggered", {"episodes": unresolved, "episode_ids": episode_ids})

    def mark_consolidated(self, envelope: dict):
        # Extrait les IDs de l'enveloppe versionnée ou d'un payload direct
        episode_ids = envelope.get("episode_ids", []) if isinstance(envelope, dict) else []
        if not episode_ids: return

        with self.store._lock:
            with sqlite3.connect(self.store.db_path) as conn:
                conn.executemany(
                    "UPDATE episodes SET consolidated = 1 WHERE episode_id = ?",
                    [(eid,) for eid in episode_ids]
                )
        self.event_bus.emit("AuditLog", {"message": f"Consolidator : {len(episode_ids)} épisodes marqués consolidés (Source: {envelope.get('source', 'unknown')}).", "level": "INFO"})