from typing import Optional, Dict, Any
from runtime.memory.models import MemoryItem, MemoryClass
from runtime.memory.store import MemoryStore
from runtime.memory.policies import MemoryPolicyEngine
from runtime.memory.retention import MemoryRetentionManager
from runtime.audit import AuditBridge, AuditAction

class MemoryGateway:
    def __init__(self, store=None, policy_engine=None, retention_manager=None):
        self.store = store or MemoryStore()
        self.policy_engine = policy_engine or MemoryPolicyEngine()
        self.retention_manager = retention_manager or MemoryRetentionManager(self.store)

    def write_memory(self, session_id: str, content: Dict[str, Any], capability_id: Optional[str], token_meta: Dict[str, Any], memory_class: MemoryClass = MemoryClass.SESSION, ttl_seconds: Optional[float] = None) -> Optional[MemoryItem]:
        if not self.policy_engine.authorize_write(capability_id, token_meta, session_id):
            return None

        item = MemoryItem(session_id=session_id, content=content, capability_id=capability_id, memory_class=memory_class)
        written_item = self.store.write(item)
        if ttl_seconds:
            self.retention_manager.set_ttl(written_item.memory_id, ttl_seconds)
        return written_item

    def read_memory(self, memory_id: str, capability_id: Optional[str], token_meta: Dict[str, Any], session_id: str = "default") -> Optional[MemoryItem]:
        if not self.policy_engine.authorize_read(capability_id, token_meta, session_id):
            return None

        # Nettoyage automatique au read pour sécurité
        self.retention_manager.purge_expired()

        item = self.store.read(memory_id)
        if item:
            AuditBridge.emit(
                component="MemoryGateway", action=AuditAction.MEMORY_READ,
                capability_id=capability_id, status="SUCCESS", metadata={"memory_id": memory_id, "hash": item.content_hash}
            )
        return item
