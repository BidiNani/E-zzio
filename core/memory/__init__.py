"""Package de gestion unifiée et résiliente de la mémoire E-ZZIO."""

from core.memory.unified_gateway import UnifiedMemoryGateway
from core.memory.legacy_manager import MemoryManager, ezzio_memory
from core.memory.strategic_memory import (
    StrategicMemoryEngine,
    strategic_memory,
    MissionOutcome,
    MemoryCategory,
    AgentReliabilityProfile,
    ModelReliabilityProfile,
    ProviderReliabilityProfile,
    TeamPerformanceProfile,
    FailurePattern,
)

__all__ = [
    "UnifiedMemoryGateway",
    "MemoryManager",
    "ezzio_memory",
    "StrategicMemoryEngine",
    "strategic_memory",
    "MissionOutcome",
    "MemoryCategory",
    "AgentReliabilityProfile",
    "ModelReliabilityProfile",
    "ProviderReliabilityProfile",
    "TeamPerformanceProfile",
    "FailurePattern",
]
