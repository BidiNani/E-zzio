from datetime import datetime, timezone
from typing import List, Optional
from runtime.memory.store import MemoryStore
from runtime.memory.expiry_store import SQLiteExpiryStore
from runtime.audit import AuditBridge, AuditAction

class MemoryRetentionManager:
    def __init__(self, memory_store: MemoryStore, expiry_store: Optional[SQLiteExpiryStore] = None, default_ttl: float = 3600.0):
        self.store = memory_store
        self.expiry_store = expiry_store or SQLiteExpiryStore()
        self.default_ttl = default_ttl

    def set_ttl(self, memory_id: str, ttl_seconds: Optional[float] = None):
        ttl = ttl_seconds if ttl_seconds is not None else self.default_ttl
        expire_at = datetime.now(timezone.utc).timestamp() + ttl
        self.expiry_store.set_expiry(memory_id, expire_at)

    def purge_expired(self) -> List[str]:
        now = datetime.now(timezone.utc).timestamp()
        expired_ids = self.expiry_store.get_expired(now)
        
        purged = []
        for mem_id in expired_ids:
            # Suppression simultanée du store RAM et du registre SQLite
            self.store.delete(mem_id)
            self.expiry_store.remove(mem_id)
            purged.append(mem_id)
            AuditBridge.emit(
                component="MemoryRetention",
                action=AuditAction.MEMORY_EXPIRE,
                metadata={"memory_id": mem_id, "reason": "ttl_exceeded_sqlite"}
            )
        return purged
