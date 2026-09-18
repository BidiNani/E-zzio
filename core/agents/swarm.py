"""
E-ZZIO Core V10.3 — Swarm Module Compatibility Alias.
"""
from core.agents.swarm.engine import (
    AgentSwarm,
    MessageType,
    SwarmConflict,
    SwarmEngine,
    SwarmLimitError,
    SwarmMessage,
    SwarmMode,
    SwarmProposal,
    SwarmState,
    swarm_engine,
)

__all__ = [
    "SwarmEngine",
    "swarm_engine",
    "AgentSwarm",
    "SwarmMessage",
    "SwarmConflict",
    "SwarmProposal",
    "MessageType",
    "SwarmMode",
    "SwarmState",
    "SwarmLimitError",
]
