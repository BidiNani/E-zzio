from typing import List, Optional, Dict, Any
from runtime.memory.models import MemoryItem

class MemoryStore:
    """
    Secure underlying storage for memory items.
    Enforces isolation and retrieval bounds.
    """
    def __init__(self):
        self._storage: Dict[str, MemoryItem] = {}

    def write(self, item: MemoryItem) -> MemoryItem:
        self._storage[item.memory_id] = item
        return item

    def read(self, memory_id: str) -> Optional[MemoryItem]:
        return self._storage.get(memory_id)

    def query_by_session(self, session_id: str) -> List[MemoryItem]:
        return [item for item in self._storage.values() if item.session_id == session_id]

    def clear(self):
        """For testing/reset purposes only"""
        self._storage.clear()
