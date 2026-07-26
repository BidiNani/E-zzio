"""
E-ZZIO Memory Runtime Layer

Phase 2.4.6.1
Secure memory storage contract and models.
"""
from runtime.memory.models import MemoryItem
from runtime.memory.store import MemoryStore

__all__ = ["MemoryItem", "MemoryStore"]
