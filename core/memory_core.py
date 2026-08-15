from runtime.adapters.memory_adapter import MemoryAdapter
from typing import List, Dict, Any, Optional

class MemoryCore:
    """Noyau unifié de gestion de la mémoire pour E-zzio."""
    def __init__(self, db_path: str = "runtime/memory/sqlite/ezzio_events.db"):
        self.store = SQLiteEventStore(db_path)

    def record_event(self, event_type: str, payload: Dict[str, Any], session_id: Optional[str] = None):
        return self.store.append(event_type, payload, session_id)

    def get_recent_memories(self, limit: int = 50) -> List[Dict[str, Any]]:
        return self.store.get_recent(limit)

    def record_interaction(self, *args, **kwargs):
        """Méthode de compatibilité pour l'enregistrement des interactions."""
        pass

# Instance singleton exportée pour les contrats sémantiques
memory_core = MemoryCore()

