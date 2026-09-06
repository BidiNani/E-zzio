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
    capabilities: List[str] = field(default_factory=list)
    risk_level: str = "LOW"
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
    depth: int = 0
    max_depth: int = 3
    budget: float = 100.0
    budget_used: float = 0.0
    children_ids: List[str] = field(default_factory=list)
    ephemeral: bool = False
    lifecycle_state: str = "READY"

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
            "capabilities": list(self.capabilities),
            "risk_level": self.risk_level,
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
            "depth": self.depth,
            "max_depth": self.max_depth,
            "budget": self.budget,
            "budget_used": self.budget_used,
            "children_ids": list(self.children_ids),
            "ephemeral": self.ephemeral,
            "lifecycle_state": self.lifecycle_state,
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
        """Enregistre la flotte canonique souveraine d'E-ZZIO (13 agents spécialisés + Master)."""
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
                capabilities=["DIALOGUE", "PLANNING", "DELEGATION", "SUPERVISION", "AGGREGATION", "NOTIFICATION"],
                risk_level="HIGH",
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
                capabilities=["CODE_READ", "CODE_WRITE", "CODE_TEST", "REPOSITORY_INSPECT"],
                risk_level="MEDIUM",
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
                capabilities=["TEST_RUN", "VALIDATE_OUTPUT", "REGRESSION_SCAN"],
                risk_level="LOW",
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
                capabilities=["SECRETS_SCAN", "INTEGRITY_CHECK", "AUDIT_VERIFY"],
                risk_level="HIGH",
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
                capabilities=["WEB_SEARCH", "READ_DOCUMENT", "ANALYZE_DOCUMENT", "SUMMARIZE"],
                risk_level="LOW",
                current_action="Forensics and codebase exploration active",
                bubble="Knowledge scouting active.",
                parent_id="master_ezzio",
                collaborator_id="coder_worker",
            ),
            AgentDescriptor(
                agent_id="web_agent",
                name="Web Navigator",
                role="Web Inspection & Online Ingestion Specialist",
                room="research_room",
                avatar="pixel_web",
                model="llama-3.3-70b-versatile",
                provider="cloud_groq",
                tools=["web.browse", "html_parser", "crawler"],
                capabilities=["WEB_BROWSE", "URL_EXTRACT", "WEB_INSPECT"],
                risk_level="LOW",
                current_action="Web discovery standing by",
                bubble="Web ingress interface online.",
                parent_id="master_ezzio",
            ),
            AgentDescriptor(
                agent_id="system_agent",
                name="System Sentinel",
                role="Operating System & Service Diagnostics Specialist",
                room="devops_dock",
                avatar="pixel_system",
                model="llama-3.3-70b-versatile",
                provider="cloud_groq",
                tools=["psutil", "system_diagnostics", "service_probe"],
                capabilities=["SYSTEM_READ", "PROCESS_READ", "SERVICE_READ", "DIAGNOSTICS"],
                risk_level="MEDIUM",
                current_action="System heartbeat and process telemetry active",
                bubble="OS metrics nominal.",
                parent_id="master_ezzio",
            ),
            AgentDescriptor(
                agent_id="cleaning_agent",
                name="Cleaning Specialist",
                role="Disk & Storage Hygiene Specialist",
                room="devops_dock",
                avatar="pixel_cleaner",
                model="llama-3.3-70b-versatile",
                provider="cloud_groq",
                tools=["disk_scanner", "cache_cleaner", "policy_evaluator"],
                capabilities=["SCAN", "CLASSIFY", "REPORT", "APPROVAL", "DELETE", "VERIFY"],
                risk_level="HIGH",
                current_action="Disk space and cache monitoring active",
                bubble="Storage hygiene policy standing by.",
                parent_id="master_ezzio",
            ),
            AgentDescriptor(
                agent_id="file_agent",
                name="File Archivist",
                role="Governed File System Operations Specialist",
                room="memory_core",
                avatar="pixel_files",
                model="qwen3.5:9b",
                provider="ollama_local",
                tools=["file_manager", "path_guard", "checksum_engine"],
                capabilities=["FILE_READ", "FILE_WRITE", "FILE_MOVE", "FILE_ARCHIVE"],
                risk_level="MEDIUM",
                current_action="Awaiting file transformation tasks",
                bubble="Governed file operations ready.",
                parent_id="master_ezzio",
            ),
            AgentDescriptor(
                agent_id="image_agent",
                name="Visual Perceiver",
                role="Multimodal Vision & Graphic Synthesis Specialist",
                room="research_room",
                avatar="pixel_vision",
                model="gemini-2.5-flash",
                provider="cloud_gemini",
                tools=["vision_inspect", "image_render", "diagram_draw"],
                capabilities=["IMAGE_GENERATE", "IMAGE_INSPECT"],
                risk_level="LOW",
                current_action="Visual processing ready",
                bubble="Multimodal perceptual engine idle.",
                parent_id="master_ezzio",
            ),
            AgentDescriptor(
                agent_id="docs_scribe",
                name="Chronicle Scribe",
                role="Architecture Documentation & Spec Publisher",
                room="docs_room",
                avatar="pixel_scribe",
                model="gemini-3.7-flash",
                provider="cloud_gemini",
                tools=["doc_writer", "markdown_validator", "pdf_exporter"],
                capabilities=["PDF_CREATE", "MARKDOWN_GENERATE", "REPORT_SYNTHESIZE"],
                risk_level="LOW",
                current_action="Compiling Living Workspace specs",
                bubble="Updating Living Workspace docs...",
                parent_id="master_ezzio",
            ),
            AgentDescriptor(
                agent_id="model_agent",
                name="Model Arbitrator",
                role="Model Qualification & Provider Health Specialist",
                room="command_center",
                avatar="pixel_model",
                model="llama-3.3-70b-versatile",
                provider="cloud_groq",
                tools=["provider_probe", "latency_meter", "benchmark_runner"],
                capabilities=["MODEL_DISCOVERY", "PROVIDER_HEALTH", "QUALIFICATION"],
                risk_level="LOW",
                current_action="Tracking provider latency and circuit-breaker states",
                bubble="Provider routing matrix optimized.",
                parent_id="master_ezzio",
            ),
            AgentDescriptor(
                agent_id="data_agent",
                name="Data Transformer",
                role="Structured Data & Extraction Specialist",
                room="memory_core",
                avatar="pixel_data",
                model="llama-3.3-70b-versatile",
                provider="cloud_groq",
                tools=["csv_parser", "json_transform", "sqlite_query"],
                capabilities=["CSV_PARSE", "JSON_TRANSFORM", "STRUCTURED_EXTRACT"],
                risk_level="LOW",
                current_action="Structured schema engines ready",
                bubble="Data transformation pipelines active.",
                parent_id="master_ezzio",
            ),
            AgentDescriptor(
                agent_id="automation_agent",
                name="Automation Engine",
                role="Governed Script Execution & Task Automator",
                room="devops_dock",
                avatar="pixel_automation",
                model="qwen3.5:9b",
                provider="ollama_local",
                tools=["script_runner", "cron_engine", "state_watch"],
                capabilities=["SCRIPT_EXEC", "SCHEDULED_TASK"],
                risk_level="HIGH",
                current_action="Awaiting governed automation schedules",
                bubble="Automation runner standing by.",
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
                capabilities=["GATEWAY_DISPATCH", "SERVICE_BRIDGE"],
                risk_level="MEDIUM",
                current_action="Serving Hermes MCP Gateway on port 8001",
                bubble="Gateway port 8001 SSE bus listening.",
                parent_id="master_ezzio",
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
                capabilities=["FTS5_SEARCH", "VECTOR_CACHE", "STATE_PERSISTENCE"],
                risk_level="LOW",
                current_action="FTS5 indexing quiescent; awaiting semantic queries",
                bubble="FTS5 indices synchronized and quiescent.",
                parent_id="master_ezzio",
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
                capabilities=["DEEP_REFACTOR"],
                risk_level="HIGH",
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

    def get_agent_by_role(self, role: str) -> Optional[AgentDescriptor]:
        """Recherche un agent par identifiant canonique de rôle ou nom de worker."""
        role_upper = role.upper().replace("-", "_").strip()
        
        # Mappages directs pour les rôles demandés
        role_alias_map = {
            "CODER_AGENT": "coder_worker",
            "CODER_WORKER": "coder_worker",
            "RESEARCH_AGENT": "researcher_scout",
            "RESEARCH_WORKER": "researcher_scout",
            "WEB_AGENT": "web_agent",
            "SYSTEM_AGENT": "system_agent",
            "SYSTEM_WORKER": "system_agent",
            "CLEANING_AGENT": "cleaning_agent",
            "CLEANING_WORKER": "cleaning_agent",
            "FILE_AGENT": "file_agent",
            "FILE_WORKER": "file_agent",
            "IMAGE_AGENT": "image_agent",
            "IMAGE_WORKER": "image_agent",
            "DOCUMENT_AGENT": "docs_scribe",
            "DOCUMENT_WORKER": "docs_scribe",
            "DOCS_SCRIBE": "docs_scribe",
            "QA_AGENT": "qa_tester",
            "QA_WORKER": "qa_tester",
            "QA_TESTER": "qa_tester",
            "SECURITY_AGENT": "sec_guard",
            "SECURITY_WORKER": "sec_guard",
            "SEC_GUARD": "sec_guard",
            "MODEL_AGENT": "model_agent",
            "DATA_AGENT": "data_agent",
            "AUTOMATION_AGENT": "automation_agent",
            "MASTER": "master_ezzio",
        }
        target_id = role_alias_map.get(role_upper)
        if target_id and target_id in self._agents:
            return self._agents[target_id]

        # Recherche floue par agent_id ou role string
        for agent in self._agents.values():
            if agent.agent_id.upper() == role_upper:
                return agent
            if role_upper in agent.role.upper():
                return agent
        return None

    def find_agents_by_capability(self, capability: str) -> List[AgentDescriptor]:
        """Retourne tous les agents possédant une capacité donnée."""
        cap_upper = capability.upper().strip()
        return [a for a in self._agents.values() if cap_upper in [c.upper() for c in a.capabilities]]

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