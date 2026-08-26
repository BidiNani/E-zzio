"""Package de gestion unifiée et résiliente de la mémoire E-ZZIO."""

from core.memory.unified_gateway import UnifiedMemoryGateway
from core.memory.legacy_manager import MemoryManager, ezzio_memory

__all__ = ["UnifiedMemoryGateway", "MemoryManager", "ezzio_memory"]
