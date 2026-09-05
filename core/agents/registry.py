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
from typing import Any, Dict, List, Optional, Set

logger = logging.getLogger("AgentRegistry")


class AgentStatus(str, Enum):
    IDLE = "IDLE"
    BUSY = "BUSY"
    WAITING_APPROVAL = "WAITING_APPROVAL"
    BLOCKED = "BLOCKED"
    DEGRADED = "DEGRADED"
    OFFLINE = "OFFLINE"
    ERROR = "ERROR"


ALLOWED_AGENT_TRANSITIONS: Dict[AgentStatus, Set[AgentStatus]] = {
    AgentStatus.IDLE: {AgentStatus.BUSY, AgentStatus.WAITING_APPROVAL, AgentStatus.DEGRADED, AgentStatus.OFFLINE, AgentStatus.ERROR},
    AgentStatus.BUSY: {AgentStatus.IDLE, AgentStatus.WAITING_APPROVAL, AgentStatus.BLOCKED, AgentStatus.DEGRADED, AgentStatus.ERROR},
    AgentStatus.WAITING_APPROVAL: {AgentStatus.BUSY, AgentStatus.IDLE, AgentStatus.BLOCKED, AgentStatus.ERROR},
    AgentStatus.BLOCKED: {AgentStatus.IDLE, AgentStatus.DEGRADED, AgentStatus.OFFLINE, AgentStatus.ERROR},
    AgentStatus.DEGRADED: {AgentStatus.IDLE, AgentStatus.BUSY, AgentStatus.OFFLINE, AgentStatus.ERROR},
    AgentStatus.OFFLINE: {AgentStatus.IDLE, AgentStatus.DEGRADED, AgentStatus.ERROR},
    AgentStatus.ERROR: {AgentStatus.IDLE, AgentStatus.OFFLINE},
}


class InvalidAgentTransitionError(Exception):
    """Levée en cas de transition illicite d'état d'un agent."""
    pass


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
                agent_id="researcher_scout",
                name="Scout Researcher",
                role="Forensic Inspector & Knowledge Scout",
                room="research_room",
                avatar="pixel_researcher",
                model="llama-3.3-70b-versatile",
                provider="cloud_groq",
                tools=["web.search", "crawl4ai", "ast_grep"],
                current_action="Hermes capability surface mapped",
                bubble="Forensics scan completed.",
                parent_id="master_ezzio",
                collaborator_id="coder_worker",
            ),
            AgentDescriptor(
                agent_id="docs_scribe",
                name="Chronicle Scribe",
                role="Architecture Documentation & Spec Publisher",
                room="docs_room",
                avatar="pixel_scribe",
                model="gemini-3.7-flash",
                provider="cloud_gemini",
                tools=["doc_writer", "markdown_validator"],
                current_action="Compiling Living Workspace specs",
                bubble="Updating Living Workspace docs...",
                parent_id="master_ezzio",
            ),
            AgentDescriptor(
                agent_id="devops_dock",
                name="Nexus DevOps",
                role="MCP Gateway & Provider Federation Dispatcher",
                room="devops_dock",
                avatar="pixel_devops",
                model="groq_router",
                provider="cloud_groq",
                tools=["hermes_mcp_gateway", "fastapi", "sse_bus"],
                current_action="Serving Hermes MCP Gateway on port 8001",
                bubble="Gateway port 8001 SSE bus listening.",
                parent_id="master_ezzio",
                collaborator_id="hermes_executor",
            ),
            AgentDescriptor(
                agent_id="memory_archivist",
                name="Mnemosyne Memory",
                role="Unified SQLite WAL + FTS5 Retrieval Gateway",
                room="memory_core",
                avatar="pixel_memory",
                model="local_fast",
                provider="local_ollama",
                tools=["fts5", "sqlite_wal", "vector_cache"],
                current_action="FTS5 indexing quiescent; awaiting semantic queries",
                bubble="FTS5 indices synchronized and quiescent.",
                parent_id="master_ezzio",
            ),
            AgentDescriptor(
                agent_id="hermes_executor",
                name="Hermes Autonomous Worker",
                role="External Reasoning & Tool Subagent (Governed)",
                room="dev_lab",
                avatar="pixel_hermes",
                model="gemini-3.7-flash",
                provider="cloud_gemini",
                tools=["mcp_tools", "browser_view", "fs_read"],
                current_action="Operating under E-ZZIO MCP Gateway confinement",
                bubble="Confinement active: executing read ops.",
                parent_id="coder_worker",
                collaborator_id="coder_worker",
            ),
            AgentDescriptor(
                agent_id="antigravity_agent",
                name="Antigravity Specialist",
                role="External Autonomous Deep Refactor Specialist",
                room="dev_lab",
                avatar="pixel_antigravity",
                model="antigravity-2.0",
                provider="agent_antigravity",
                tools=["agy_cli"],
                status=AgentStatus.ERROR,
                current_action="Standing by: BLOCKED_BY_EXTERNAL_QUOTA",
                bubble="Quota limit reached: standby fail-safe mode.",
                parent_id="master_ezzio",
            ),
        ]
        for desc in defaults:
            self._agents[desc.agent_id] = desc

    def reset_to_defaults(self) -> None:
        """Réinitialise les agents à leur état canonique d'origine."""
        self._agents.clear()
        self._register_default_agents()


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
        force: bool = False,
    ) -> None:
        agent = self._agents.get(agent_id)
        if not agent:
            logger.warning("Agent '%s' not registered", agent_id)
            return

        if not force and agent.status != status:
            allowed = ALLOWED_AGENT_TRANSITIONS.get(agent.status, set())
            if status not in allowed:
                raise InvalidAgentTransitionError(
                    f"Transition interdite pour '{agent_id}': {agent.status.value} -> {status.value}"
                )

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
            if agent.status in (AgentStatus.DEGRADED, AgentStatus.OFFLINE):
                agent.status = AgentStatus.IDLE

    def check_heartbeats(self, degraded_threshold_sec: float = 30.0, offline_threshold_sec: float = 90.0) -> List[Dict[str, Any]]:
        """Vérifie les battements de cœur et dégrade/met hors-ligne les agents silencieux."""
        now = time.time()
        events = []
        for agent in self._agents.values():
            if agent.is_master:
                continue
            elapsed = now - agent.last_heartbeat
            if elapsed >= offline_threshold_sec and agent.status != AgentStatus.OFFLINE:
                old_st = agent.status
                agent.status = AgentStatus.OFFLINE
                agent.current_action = f"Offline (heartbeat elapsed {int(elapsed)}s)"
                events.append({"agent_id": agent.agent_id, "from": old_st.value, "to": "OFFLINE", "elapsed": elapsed})
            elif elapsed >= degraded_threshold_sec and agent.status not in (AgentStatus.DEGRADED, AgentStatus.OFFLINE, AgentStatus.ERROR):
                old_st = agent.status
                agent.status = AgentStatus.DEGRADED
                agent.current_action = f"Degraded (silent {int(elapsed)}s)"
                events.append({"agent_id": agent.agent_id, "from": old_st.value, "to": "DEGRADED", "elapsed": elapsed})
        return events


agent_registry = AgentRegistry()