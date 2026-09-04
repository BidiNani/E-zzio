"""
E-ZZIO Core V9.2 — Sovereign Dynamic Agent Registry & Lifecycle Engine.
Gère l'enregistrement, les états d'activité, les heartbeats et l'isolation des agents.
"""
from __future__ import annotations

import asyncio
import logging
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional

logger = logging.getLogger("AgentRegistry")


class AgentStatus(str, Enum):
    IDLE = "IDLE"
    BUSY = "BUSY"
    WAITING_APPROVAL = "WAITING_APPROVAL"
    BLOCKED = "BLOCKED"
    DEGRADED = "DEGRADED"
    OFFLINE = "OFFLINE"


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass
class AgentDescriptor:
    agent_id: str
    name: str
    role: str
    room: str
    avatar: str
    model: str
    provider: str
    tools: List[str] = field(default_factory=list)
    status: AgentStatus = AgentStatus.IDLE
    current_action: str = "Ready"
    progress: int = 0
    current_task_id: Optional[str] = None
    bubble: Optional[str] = None
    is_master: bool = False
    parent_id: Optional[str] = None
    collaborator_id: Optional[str] = None
    last_heartbeat: float = field(default_factory=time.time)
    registered_at: str = field(default_factory=utc_now)
    code_activity: Optional[Dict[str, Any]] = None
    terminal_logs: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "agent_id": self.agent_id,
            "name": self.name,
            "role": self.role,
            "room": self.room,
            "avatar": self.avatar,
            "model": self.model,
            "provider": self.provider,
            "tools": list(self.tools),
            "status": self.status.value,
            "current_action": self.current_action,
            "progress": self.progress,
            "task_id": self.current_task_id,
            "bubble": self.bubble,
            "is_master": self.is_master,
            "parent_id": self.parent_id,
            "collaborator_id": self.collaborator_id,
            "last_heartbeat": self.last_heartbeat,
            "registered_at": self.registered_at,
            "code_activity": self.code_activity,
            "terminal_logs": self.terminal_logs[-20:],  # limiter aux 20 derniers logs
        }


class AgentRegistry:
    """Registre singleton souverain de gestion d'agents."""

    _instance: Optional[AgentRegistry] = None

    def __new__(cls, *args, **kwargs):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if getattr(self, "_initialized", False):
            return
        self._agents: Dict[str, AgentDescriptor] = {}
        self._lock = asyncio.Lock()
        self._sync_lock = asyncio.Lock()
        self._register_default_agents()
        self._initialized = True

    def _register_default_agents(self) -> None:
        """Enregistre la flotte canonique souveraine d'E-ZZIO."""
        defaults = [
            AgentDescriptor(
                agent_id="master_ezzio",
                name="E-ZZIO",
                role="Sovereign Core Governor & Policy Authority",
                room="command_center",
                avatar="crown_master",
                model="gemini-3.7-flash",
                provider="cloud_gemini",
                tools=["CapabilityPolicy", "AuditLedger", "ModelRouter", "UnifiedGateway"],
                is_master=True,
                current_action="Supervising Platform & Enforcing Frozen Core Policy",
                bubble="Sovereign OS fully governed.",
            ),
            AgentDescriptor(
                agent_id="coder_worker",
                name="Coder-Worker",
                role="Lead Autonomous Software Engineer",
                room="dev_lab",
                avatar="robot_coder",
                model="qwen3.5:9b",
                provider="ollama_local",
                tools=["LocalExecution", "CodePatch", "GitEngine", "Sandbox"],
                current_action="Platform engineering active",
                bubble="Autonomous software engineering in progress.",
            ),
            AgentDescriptor(
                agent_id="qa_tester",
                name="QA-Validator",
                role="Continuous Test & Forensic Auditor",
                room="test_lab",
                avatar="microscope_qa",
                model="phi4-mini:latest",
                provider="ollama_local",
                tools=["PytestRunner", "ForensicScanner", "RegressionGate"],
                current_action="Monitoring test execution integrity",
                bubble="100% test integrity enforced.",
            ),
            AgentDescriptor(
                agent_id="sec_guard",
                name="Security-Guard",
                role="Cryptographic Vault & HITL Arbiter",
                room="security_vault",
                avatar="shield_sec",
                model="gemma4e4b:latest",
                provider="ollama_local",
                tools=["CapabilityGuard", "ApprovalManager", "SecretsVault", "AuditLedger"],
                current_action="Audit ledger hash-chain inspection",
                bubble="Cryptographic verification active.",
            ),
            AgentDescriptor(
                agent_id="research_agent",
                name="Research-Specialist",
                role="Knowledge Harvester & Web Researcher",
                room="research_room",
                avatar="book_research",
                model="qwen3.5:9b",
                provider="ollama_local",
                tools=["WebSearchMCP", "Crawl4AI", "Tavily", "RAGMemory"],
                current_action="Sovereign indexing ready",
                bubble="Research capability online.",
            ),
        ]
        for desc in defaults:
            self._agents[desc.agent_id] = desc

    def register(self, desc: AgentDescriptor) -> None:
        self._agents[desc.agent_id] = desc

    def get_agent(self, agent_id: str) -> Optional[AgentDescriptor]:
        return self._agents.get(agent_id)

    def list_agents(self) -> List[AgentDescriptor]:
        return list(self._agents.values())

    def update_status(
        self,
        agent_id: str,
        status: AgentStatus,
        current_action: Optional[str] = None,
        progress: Optional[int] = None,
        task_id: Optional[str] = None,
        bubble: Optional[str] = None,
        log_line: Optional[str] = None,
    ) -> None:
        agent = self._agents.get(agent_id)
        if not agent:
            logger.warning("Agent '%s' not registered", agent_id)
            return
        agent.status = status
        agent.last_heartbeat = time.time()
        if current_action is not None:
            agent.current_action = current_action
        if progress is not None:
            agent.progress = max(0, min(100, progress))
        if task_id is not None:
            agent.current_task_id = task_id
        if bubble is not None:
            agent.bubble = bubble
        if log_line:
            agent.terminal_logs.append(f"[{utc_now()}] {log_line}")

    def heartbeat(self, agent_id: str) -> None:
        agent = self._agents.get(agent_id)
        if agent:
            agent.last_heartbeat = time.time()


agent_registry = AgentRegistry()