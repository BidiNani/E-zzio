"""
E-ZZIO Sovereign Agent Swarm — Engine & Continuous Quality Sentinels.
"""
from core.agents.swarm.engine import (
    SwarmEngine,
    swarm_engine,
    AgentSwarm,
    SwarmMessage,
    SwarmConflict,
    SwarmProposal,
    MessageType,
    SwarmMode,
    SwarmState,
    SwarmLimitError,
)
from core.agents.swarm.inspector import InspectorAgent
from core.agents.swarm.watcher import WatcherAgent
from core.agents.swarm.sentinel import SentinelAgent

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
