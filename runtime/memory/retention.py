from datetime import datetime, timezone
from typing import List, Dict, Any, Optional
from runtime.memory.store import MemoryStore
from runtime.audit import AuditBridge, AuditAction

class MemoryRetentionManager:
    """
    Manages memory lifetime, automatic expiration, and policy-driven purge.
    """
    def __init__(self, memory_store: MemoryStore, default_ttl_seconds: float = 3600.0):
        self.store = memory_store
        self.default_ttl = default_ttl_seconds
        self._expiration_registry: Dict[str, datetime] = {}

    def set_ttl(self, memory_id: str, ttl_seconds: Optional[float] = None):
        """Sets absolute expiration timestamp for a memory item."""
        ttl = ttl_seconds if ttl_seconds is not None else self.default_ttl
        expire_at = datetime.now(timezone.utc).timestamp() + ttl
        self._expiration_registry[memory_id] = datetime.fromtimestamp(expire_at, tz=timezone.utc)

    def is_expired(self, memory_id: str) -> bool:
        """Checks if a memory item has exceeded its lifetime."""
        expire_at = self._expiration_registry.get(memory_id)
        if not expire_at:
            return False
        return datetime.now(timezone.utc) > expire_at

    def purge_expired(self) -> List[str]:
        """Purges expired items and records audit events."""
        purged = []
        now = datetime.now(timezone.utc)
        for mem_id, expire_at in list(self._expiration_registry.items()):
            if now > expire_at:
                purged.append(mem_id)
                del self._expiration_registry[mem_id]
                # Emission audit de suppression
                AuditBridge.emit(
                    component="MemoryRetention",
                    action=AuditAction.MEMORY_EXPIRE,
                    metadata={"memory_id": mem_id, "reason": "ttl_exceeded"}
                )
        return purged
