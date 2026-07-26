from typing import Optional, Dict, Any, List
from runtime.memory.models import MemoryItem
from runtime.memory.store import MemoryStore
from runtime.memory.policies import MemoryPolicyEngine
from runtime.memory.retention import MemoryRetentionManager

class MemoryGateway:
    """
    Unified access gateway orchestrating policy checks, storage, 
    and retention for memory operations.
    """
    def __init__(
        self,
        store: Optional[MemoryStore] = None,
        policy_engine: Optional[MemoryPolicyEngine] = None,
        retention_manager: Optional[MemoryRetentionManager] = None
    ):
        self.store = store or MemoryStore()
        self.policy_engine = policy_engine or MemoryPolicyEngine()
        self.retention_manager = retention_manager or MemoryRetentionManager(self.store)

    def write_memory(
        self,
        session_id: str,
        content: Dict[str, Any],
        capability_id: Optional[str],
        token_meta: Dict[str, Any],
        ttl_seconds: Optional[float] = None
    ) -> Optional[MemoryItem]:
        """
        Enforces policy and writes a memory item if authorized.
        """
        if not self.policy_engine.authorize_write(capability_id, token_meta, session_id):
            return None

        item = MemoryItem(
            session_id=session_id,
            content=content,
            capability_id=capability_id
        )
        written_item = self.store.write(item)
        if ttl_seconds:
            self.retention_manager.set_ttl(written_item.memory_id, ttl_seconds)
        return written_item

    def read_memory(
        self,
        memory_id: str,
        capability_id: Optional[str],
        token_meta: Dict[str, Any],
        session_id: str = "default"
    ) -> Optional[MemoryItem]:
        """
        Enforces policy, checks expiration, and retrieves a memory item.
        """
        if not self.policy_engine.authorize_read(capability_id, token_meta, session_id):
            return None

        if self.retention_manager.is_expired(memory_id):
            return None

        return self.store.read(memory_id)
