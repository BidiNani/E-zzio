from typing import Dict, Any, Optional
from core.evidence_store import EvidenceStore


class MemoryCore:
    """Noyau unifié de gestion de la mémoire pour E-zzio."""

    def __init__(self, db_path: str = "runtime/memory/sqlite/ezzio_events.db"):
        self.store = EvidenceStore(db_path)

    async def record_event(self, event_type: str, payload: Dict[str, Any], session_id: Optional[str] = None):
        return await self.store.store(provider="memory_core", mode=event_type, query=str(payload))
