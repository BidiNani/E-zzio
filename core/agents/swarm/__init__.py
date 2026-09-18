"""
E-ZZIO Sovereign Agent Swarm — Engine & Continuous Quality Sentinels.
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
from core.agents.swarm.inspector import InspectorAgent
from core.agents.swarm.sentinel import SentinelAgent
from core.agents.swarm.watcher import WatcherAgent

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
    "InspectorAgent",
    "WatcherAgent",
    "SentinelAgent",
]
