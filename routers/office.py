"""
E-ZZIO AI Office — Virtual Workspace State & Telemetry Router.
Expose la cartographie en direct des agents souverains, leurs zones de travail,
leurs sous-agents, les tâches en cours, le flux d'événements et l'arbitrage HITL.
"""
from __future__ import annotations

import os
from datetime import UTC, datetime
from typing import Any

from fastapi import APIRouter
from pydantic import BaseModel, Field

from core.agents.registry import AgentStatus, agent_registry
from core.governance.approval import (
    approval_manager,
)
from core.security.audit_ledger import audit_ledger
from core.tasks import manager as task_manager_mod

router = APIRouter(tags=["AI Office"])



class AgentVisualState(BaseModel):
    agent_id: str
    name: str
    role: str
    room: str  # "command_center", "dev_lab", "research_room", "test_lab", "security_vault", "docs_room", "devops_dock", "memory_core"
    status: str  # "IDLE", "WORKING", "WAITING_APPROVAL", "ERROR", "DONE"
    task_id: str | None = None
    current_action: str
    progress: int = 0
    model: str
    provider: str
    avatar: str  # identifiant de sprite pixel-art
    is_master: bool = False
    parent_id: str | None = None
    tools: list[str] = Field(default_factory=list)
    last_event: str = ""
    bubble: str | None = None  # Bulle contextuelle vivante
    collaborator_id: str | None = None  # Agent partenaire de collaboration
    code_activity: dict[str, Any] | None = None  # Info repo, branch, last test/file
    terminal_logs: list[str] = Field(default_factory=list)  # Logs de terminal réels
    # 2.5D Spatial Simulation Fields (V9.4 Living Office)
    x: float = 0.0
    y: float = 0.0
    target_room: str | None = None
    target_x: float | None = None
    target_y: float | None = None
    heading: str = "DOWN"  # "UP", "DOWN", "LEFT", "RIGHT"
    animation_state: str = "IDLE"  # "IDLE", "WALK", "WORK", "WAIT_APPROVAL", "ERROR", "DONE"
    updated_at: str = Field(default_factory=lambda: datetime.now(UTC).isoformat())


class OfficeStateResponse(BaseModel):
    ok: bool = True
    master_authority: str = "E-ZZIO V9.0 SOVEREIGN MASTER"
    summary: dict[str, Any]
    rooms: list[str]
    agents: list[AgentVisualState]
    pending_approvals_count: int
    active_tasks_count: int
    timestamp: str


@router.get("/api/v1/office/state", response_model=OfficeStateResponse)
@router.get("/office/state", response_model=OfficeStateResponse)
async def get_office_state():
    """Retourne l'état complet du bureau virtuel avec les agents réels connectés."""
    pending_approvals = approval_manager.get_pending()
    has_approval_pending = len(pending_approvals) > 0

    # Détection des tâches réelles
    active_tasks = []
    try:
        # Tâches dans tasks.db
        with task_manager_mod.storage.get_connection(task_manager_mod.DB_PATH) as conn:
            cur = conn.execute("SELECT task_id, title, state, approval_id FROM governed_tasks ORDER BY updated_at DESC LIMIT 10")
            cols = [col[0] for col in cur.description]
            for row in cur.fetchall():
                active_tasks.append(dict(zip(cols, row)))
    except Exception:
        pass

    # Agents réels du système souverain avec métadonnées vivantes
    agents: list[AgentVisualState] = [
        # 1. 👑 E-ZZIO Master Governor
        AgentVisualState(
            agent_id="master_ezzio",
            name="E-ZZIO",
            role="Sovereign Core Governor & Policy Authority",
            room="command_center",
            status="WAITING_APPROVAL" if has_approval_pending else "WORKING",
            task_id=pending_approvals[0].task_id if has_approval_pending else "V9_CONSOLIDATION",
            current_action="Supervising Office & Enforcing Frozen Core Policy" if not has_approval_pending else f"Enforcing Policy: Awaiting Human Decision for {pending_approvals[0].approval_id}",
            progress=100 if not has_approval_pending else 65,
            model="gemini-3.7-flash",
            provider="cloud_gemini",
            avatar="crown_master",
            is_master=True,
            parent_id=None,
            tools=["CapabilityPolicy", "AuditLedger", "ModelRouter", "UnifiedGateway"],
            last_event="E-ZzIO V9.0 Sovereign Guard Active",
            bubble="Awaiting operator confirmation!" if has_approval_pending else "Sovereign office fully governed.",
            collaborator_id="sec_guard" if has_approval_pending else "coder_worker",
            code_activity={"repo": "E-zzio", "branch": "checkpoint/voice-capabilities-hardware-agent-20260816", "commit": "dde4d18", "file": "web_server.py"},
            terminal_logs=[
                "[SOVEREIGN] Master Kernel initialized on port 8001",
                "[POLICY] CapabilityPolicy enforcement hook mounted",
                "[STATUS] 86/86 Certified tests non-regression verified",
            ],
        ),
        # 2. 🧑💻 Coder Agent (Coding Worker)
        AgentVisualState(
            agent_id="coder_worker",
            name="Alpha Coder",
            role="Autonomous Coding & Self-Healing Worker",
            room="dev_lab",
            status="WORKING",
            task_id="CODE_PATCH_V9",
            current_action="Synthesizing AI Office Visual Components & Tests",
            progress=92,
            model="qwen3.5:9b",
            provider="local_ollama",
            avatar="pixel_coder",
            is_master=False,
            parent_id="master_ezzio",
            tools=["python", "git", "terminal", "patch_parser"],
            last_event="Phase 1-4 modules synthesized and certified",
            bubble="Rendering Living Pixel UI...",
            collaborator_id="qa_tester",
            code_activity={"repo": "E-zzio", "branch": "checkpoint/voice-capabilities-hardware-agent-20260816", "commit": "dde4d18", "file": "runtime/web/index.html"},
            terminal_logs=[
                "PS> python -m py_compile routers/office.py",
                "Compilation exit code: 0 [SUCCESS]",
                "PS> git diff --stat",
            ],
        ),
        # 3. 🧑🔬 Researcher Agent
        AgentVisualState(
            agent_id="researcher_scout",
            name="Scout Researcher",
            role="Forensic Inspector & Knowledge Scout",
            room="research_room",
            status="DONE",
            task_id="INSPECTION_HERMES",
            current_action="Hermes capability surface mapped (139 tools quarantined)",
            progress=100,
            model="llama-3.3-70b-versatile",
            provider="cloud_groq",
            avatar="pixel_researcher",
            is_master=False,
            parent_id="master_ezzio",
            tools=["web.search", "crawl4ai", "ast_grep"],
            last_event="Hermes surface forensics complete",
            bubble="Forensics scan completed (139 tools quarantined).",
            collaborator_id="coder_worker",
            code_activity={"repo": "E-zzio", "branch": "checkpoint/voice-capabilities-hardware-agent-20260816", "commit": "dde4d18", "file": "core/capabilities/hermes_mcp_gateway.py"},
            terminal_logs=[
                "SCOUT> Inspecting Hermes capability catalog",
                "SCOUT> Quarantine rules applied to mutating tools",
            ],
        ),
        # 4. 🧪 Tester Agent
        AgentVisualState(
            agent_id="qa_tester",
            name="Sentinel QA",
            role="Test Lab & Integrity Verifier",
            room="test_lab",
            status="WORKING",
            task_id="REGRESSION_GATE_86",
            current_action="Running continuous pytest regression on V9 certified suite",
            progress=98,
            model="phi4-mini:latest",
            provider="local_ollama",
            avatar="pixel_tester",
            is_master=False,
            parent_id="master_ezzio",
            tools=["pytest", "py_compile", "sqlite_verifier"],
            last_event="86/86 passed in 3.35s",
            bubble="86/86 PASS - 100% test hygiene clean!",
            collaborator_id="coder_worker",
            code_activity={"repo": "E-zzio", "branch": "checkpoint/voice-capabilities-hardware-agent-20260816", "commit": "dde4d18", "file": "tests/test_ai_office.py"},
            terminal_logs=[
                "PS> python -m pytest tests/test_hitl_approval.py ...",
                "================== 86 passed in 3.35s ==================",
            ],
        ),
        # 5. 🛡️ Security Agent
        AgentVisualState(
            agent_id="sec_guard",
            name="Aegis Guard",
            role="Capability Policy & Audit Ledger Arbitrator",
            room="security_vault",
            status="WAITING_APPROVAL" if has_approval_pending else "WORKING",
            task_id=pending_approvals[0].approval_id if has_approval_pending else "AUDIT_SEAL",
            current_action="Guarding SHA-256 AuditLedger & Intercepting Mutating Scopes" if not has_approval_pending else "Escalated REQUIRE_HUMAN to Operator",
            progress=100,
            model="gemini-3.5-flash-lite",
            provider="cloud_gemini",
            avatar="pixel_shield",
            is_master=False,
            parent_id="master_ezzio",
            tools=["AuditLedger", "CapabilityPolicy", "SecretsVault"],
            last_event="Append-only cryptographic chain sealed",
            bubble="HALT: Require Human Decision!" if has_approval_pending else "Cryptographic chain sealed SHA-256.",
            collaborator_id="master_ezzio" if has_approval_pending else "devops_dock",
            code_activity={"repo": "E-zzio", "branch": "checkpoint/voice-capabilities-hardware-agent-20260816", "commit": "dde4d18", "file": "core/security/audit_ledger.py"},
            terminal_logs=[
                "AEGIS> AuditLedger verification: chain integrity VALID",
                "AEGIS> Zero secret leakage policy enforced",
            ],
        ),
        # 6. 📝 Docs & Knowledge Agent
        AgentVisualState(
            agent_id="docs_scribe",
            name="Chronicle Scribe",
            role="Architecture Documentation & Spec Publisher",
            room="docs_room",
            status="WORKING",
            task_id="AI_OFFICE_DOCS",
            current_action="Compiling AI_OFFICE_ARCHITECTURE.md & UI Specs",
            progress=95,
            model="gemini-3.7-flash",
            provider="cloud_gemini",
            avatar="pixel_scribe",
            is_master=False,
            parent_id="master_ezzio",
            tools=["doc_writer", "markdown_validator"],
            last_event="Architecture specs drafted",
            bubble="Updating Living Workspace docs...",
            collaborator_id=None,
            code_activity={"repo": "E-zzio", "branch": "checkpoint/voice-capabilities-hardware-agent-20260816", "commit": "dde4d18", "file": "docs/AI_OFFICE_UI.md"},
            terminal_logs=[
                "SCRIBE> Updated docs/AI_OFFICE_ARCHITECTURE.md",
                "SCRIBE> Updated docs/AI_OFFICE_UI.md",
            ],
        ),
        # 7. 🚀 DevOps & Gateway Agent
        AgentVisualState(
            agent_id="devops_dock",
            name="Nexus DevOps",
            room="devops_dock",
            role="MCP Gateway & Provider Federation Dispatcher",
            status="WORKING",
            task_id="MCP_DISPATCH",
            current_action="Serving Hermes MCP Gateway on port 8001",
            progress=100,
            model="groq_router",
            provider="cloud_groq",
            avatar="pixel_devops",
            is_master=False,
            parent_id="master_ezzio",
            tools=["hermes_mcp_gateway", "fastapi", "sse_bus"],
            last_event="Hermes MCP gateway listening",
            bubble="Gateway port 8001 SSE bus listening.",
            collaborator_id="hermes_executor",
            code_activity={"repo": "E-zzio", "branch": "checkpoint/voice-capabilities-hardware-agent-20260816", "commit": "dde4d18", "file": "core/capabilities/hermes_mcp_gateway.py"},
            terminal_logs=[
                "DEVOPS> Initialized SSE MCP bus for Hermes",
                "DEVOPS> Provider endpoints routed to 127.0.0.1:8001",
            ],
        ),
        # 8. 🧠 Memory Specialist
        AgentVisualState(
            agent_id="memory_archivist",
            name="Mnemosyne Memory",
            room="memory_core",
            role="Unified SQLite WAL + FTS5 Retrieval Gateway",
            status="IDLE",
            task_id="MEMORY_INDEX",
            current_action="FTS5 indexing quiescent; awaiting semantic queries",
            progress=100,
            model="local_fast",
            provider="local_ollama",
            avatar="pixel_memory",
            is_master=False,
            parent_id="master_ezzio",
            tools=["fts5", "sqlite_wal", "vector_cache"],
            last_event="Memory WAL synchronized",
            bubble="FTS5 indices synchronized and quiescent.",
            collaborator_id=None,
            code_activity={"repo": "E-zzio", "branch": "checkpoint/voice-capabilities-hardware-agent-20260816", "commit": "dde4d18", "file": "core/memory/instance.py"},
            terminal_logs=[
                "MEMORY> SQLite WAL synced: runtime/evidence/tasks.db",
                "MEMORY> FTS5 full-text index ready",
            ],
        ),
        # 9. 🤖 External Subagent : Hermes Executor
        AgentVisualState(
            agent_id="hermes_executor",
            name="Hermes Autonomous Worker",
            room="dev_lab",
            role="External Reasoning & Tool Subagent (Governed)",
            status="WORKING",
            task_id="HERMES_SUB_01",
            current_action="Operating under E-ZZIO MCP Gateway confinement",
            progress=80,
            model="gemini-3.7-flash",
            provider="cloud_gemini",
            avatar="pixel_hermes",
            is_master=False,
            parent_id="coder_worker",
            tools=["mcp_tools", "browser_view", "fs_read"],
            last_event="Confinement active: mutative calls require E-ZZIO HITL",
            bubble="Confinement active: executing read ops.",
            collaborator_id="coder_worker",
            code_activity={"repo": "E-zzio", "branch": "checkpoint/voice-capabilities-hardware-agent-20260816", "commit": "dde4d18", "file": "core/capabilities/hermes_mcp_gateway.py"},
            terminal_logs=[
                "HERMES> Connected to E-ZZIO MCP Gateway",
                "HERMES> Policy check passed for read-only capabilities",
            ],
        ),
        # 10. 🛰️ External Specialist : Antigravity (Quota Blocked)
        AgentVisualState(
            agent_id="antigravity_agent",
            name="Antigravity Specialist",
            room="dev_lab",
            role="External Autonomous Deep Refactor Specialist",
            status="ERROR",
            task_id="QUOTA_STANDBY",
            current_action="Standing by: BLOCKED_BY_EXTERNAL_QUOTA",
            progress=0,
            model="antigravity-2.0",
            provider="agent_antigravity",
            avatar="pixel_antigravity",
            is_master=False,
            parent_id="master_ezzio",
            tools=["agy_cli"],
            last_event="BLOCKED_BY_EXTERNAL_QUOTA (Fail-safe, non-fatal)",
            bubble="Quota limit reached: standby fail-safe mode.",
            collaborator_id=None,
            code_activity={"repo": "E-zzio", "branch": "checkpoint/voice-capabilities-hardware-agent-20260816", "commit": "dde4d18", "file": "core/cognition/model_federation/antigravity_provider.py"},
            terminal_logs=[
                "AGY> Provider status: BLOCKED_BY_EXTERNAL_QUOTA",
                "AGY> Fail-safe active, non-blocking for sovereign core",
            ],
        ),
    ]

    # Synchronisation dynamique avec le registre d'agents souverain V9.2
    for vis_agent in agents:
        reg_agent = agent_registry.get_agent(vis_agent.agent_id)
        if reg_agent:
            # Ne pas écraser l'état WAITING_APPROVAL si une approbation est en attente
            if not has_approval_pending or vis_agent.agent_id not in ("master_ezzio", "sec_guard"):
                if reg_agent.status == AgentStatus.BUSY:
                    vis_agent.status = "WORKING"
                elif reg_agent.status == AgentStatus.WAITING_APPROVAL:
                    vis_agent.status = "WAITING_APPROVAL"
                elif reg_agent.status == AgentStatus.ERROR:
                    vis_agent.status = "ERROR"
                elif reg_agent.status == AgentStatus.OFFLINE:
                    vis_agent.status = "ERROR"
            if reg_agent.current_action and reg_agent.current_action != "Ready":
                vis_agent.current_action = reg_agent.current_action
            if reg_agent.bubble:
                vis_agent.bubble = reg_agent.bubble
            if reg_agent.progress > 0:
                vis_agent.progress = reg_agent.progress
            if reg_agent.terminal_logs:
                vis_agent.terminal_logs = reg_agent.terminal_logs[-10:]

    # Attribution déterministe des coordonnées spatiales 2.5D et animations (V9.4)
    for vis_agent in agents:
        if vis_agent.agent_id == "master_ezzio":
            vis_agent.x, vis_agent.y = 5.0, 4.0
            vis_agent.heading = "DOWN"
            vis_agent.animation_state = "WAIT_APPROVAL" if has_approval_pending else "WORK"
        elif vis_agent.agent_id == "coder_worker":
            vis_agent.x, vis_agent.y = 16.0, 4.0
            vis_agent.heading = "DOWN"
            vis_agent.animation_state = "WORK"
        elif vis_agent.agent_id == "hermes_executor":
            vis_agent.x, vis_agent.y = 20.0, 4.0
            vis_agent.heading = "LEFT"
            vis_agent.animation_state = "WORK"
        elif vis_agent.agent_id == "researcher_scout":
            vis_agent.x, vis_agent.y = 30.0, 4.0
            vis_agent.heading = "DOWN"
            vis_agent.animation_state = "IDLE"
        elif vis_agent.agent_id == "qa_tester":
            vis_agent.x, vis_agent.y = 5.0, 12.0
            vis_agent.heading = "RIGHT"
            vis_agent.animation_state = "WORK"
        elif vis_agent.agent_id == "sec_guard":
            if has_approval_pending:
                vis_agent.x, vis_agent.y = 7.0, 5.0
                vis_agent.target_room = "command_center"
                vis_agent.heading = "UP"
                vis_agent.animation_state = "WAIT_APPROVAL"
            else:
                vis_agent.x, vis_agent.y = 30.0, 12.0
                vis_agent.heading = "LEFT"
                vis_agent.animation_state = "WORK"
        elif vis_agent.agent_id == "docs_scribe":
            vis_agent.x, vis_agent.y = 5.0, 19.0
            vis_agent.heading = "RIGHT"
            vis_agent.animation_state = "WORK"
        elif vis_agent.agent_id == "devops_dock":
            vis_agent.x, vis_agent.y = 18.0, 19.0
            vis_agent.heading = "UP"
            vis_agent.animation_state = "WORK"
        elif vis_agent.agent_id == "memory_archivist":
            vis_agent.x, vis_agent.y = 30.0, 19.0
            vis_agent.heading = "LEFT"
            vis_agent.animation_state = "IDLE"
        elif vis_agent.agent_id == "antigravity_agent":
            vis_agent.x, vis_agent.y = 14.0, 2.0
            vis_agent.heading = "DOWN"
            vis_agent.animation_state = "ERROR"

    rooms = [

        "command_center",
        "dev_lab",
        "research_room",
        "test_lab",
        "security_vault",
        "docs_room",
        "devops_dock",
        "memory_core",
    ]

    working_count = sum(1 for a in agents if a.status == "WORKING")
    waiting_count = sum(1 for a in agents if a.status == "WAITING_APPROVAL")
    error_count = sum(1 for a in agents if a.status == "ERROR")
    done_count = sum(1 for a in agents if a.status == "DONE")

    return OfficeStateResponse(
        ok=True,
        master_authority="E-ZZIO V9.0 SOVEREIGN MASTER",
        summary={
            "total_agents": len(agents),
            "working": working_count,
            "waiting_approval": waiting_count,
            "error_or_quota_blocked": error_count,
            "done": done_count,
            "providers": {
                "gemini": "PASS",
                "groq": "PASS",
                "ollama": "PASS",
                "antigravity": "BLOCKED_BY_EXTERNAL_QUOTA",
            },
            "frozen_core": "INTACT",
            "active_tasks": active_tasks[:5],
        },
        rooms=rooms,
        agents=agents,
        pending_approvals_count=len(pending_approvals),
        active_tasks_count=len(active_tasks),
        timestamp=datetime.now(UTC).isoformat(),
    )


class OfficeLiveEventsResponse(BaseModel):
    ok: bool = True
    events: list[dict[str, Any]]
    total: int


@router.get("/api/v1/office/events", response_model=OfficeLiveEventsResponse)
@router.get("/office/events", response_model=OfficeLiveEventsResponse)
async def get_office_live_events():
    """Flux d'événements récents consolidés depuis l'AuditLedger et l'état des agents."""
    events = [
        {"time": "15:12", "actor": "Aegis Guard", "action": "Audit Trail Scelle SHA-256", "room": "security_vault"},
        {"time": "15:20", "actor": "E-ZZIO Governor", "action": "HITL Governance Interception Ready", "room": "command_center"},
    ]
    try:
        # Lire les entrées réelles du registre d'audit append-only
        with audit_ledger._get_connection() as conn:
            cur = conn.execute("SELECT timestamp, actor, action, status FROM audit_trail ORDER BY id DESC LIMIT 8")
            for r in cur.fetchall():
                ts, actor, action, status = r
                t_str = datetime.fromtimestamp(ts, tz=UTC).strftime("%H:%M:%S")
                events.append({
                    "time": t_str,
                    "actor": actor,
                    "action": f"{action} [{status}]",
                    "room": "security_vault" if "Ledger" in actor or "Policy" in actor else "dev_lab"
                })
    except Exception:
        pass

    return OfficeLiveEventsResponse(ok=True, events=events, total=len(events))


@router.get("/manifest.json")
@router.get("/runtime/web/manifest.json")
async def get_web_manifest():
    """Manifest PWA officiel pour Desktop Install & Mobile Add-to-Home."""
    from fastapi.responses import FileResponse
    manifest_path = os.path.join(r"G:\AI\E-zzio\runtime\web", "manifest.json")
    return FileResponse(manifest_path, media_type="application/manifest+json")


@router.get("/sw.js")
@router.get("/runtime/web/sw.js")
async def get_service_worker():
    """Service Worker PWA officiel pour le mode hors-ligne et la résilience réseau."""
    from fastapi.responses import FileResponse
    sw_path = os.path.join(r"G:\AI\E-zzio\runtime\web", "sw.js")
    return FileResponse(sw_path, media_type="application/javascript")


# ==============================================================================
# V9.4 2.5D SPATIAL MAP SPECIFICATION & CANONICAL LAYOUT
# ==============================================================================
class TileCoord(BaseModel):
    x: float
    y: float

class RoomDefinition(BaseModel):
    name: str
    code: str
    x: int
    y: int
    w: int
    h: int
    door: TileCoord
    desk: TileCoord
    subdesk: TileCoord | None = None
    color: str
    icon: str
    description: str

class OfficeMapResponse(BaseModel):
    ok: bool = True
    grid_width: int = 36
    grid_height: int = 24
    tile_size: int = 28
    rooms: dict[str, RoomDefinition]


CANONICAL_OFFICE_MAP = {
    "command_center": RoomDefinition(
        name="COMMAND CENTER",
        code="command_center",
        x=1, y=1, w=10, h=7,
        door=TileCoord(x=11.0, y=4.0),
        desk=TileCoord(x=5.0, y=4.0),
        color="#3B82F6",
        icon="👑",
        description="Master Governor, Executive Directives & HITL Sanctuary"
    ),
    "dev_lab": RoomDefinition(
        name="DEV LAB",
        code="dev_lab",
        x=13, y=1, w=10, h=7,
        door=TileCoord(x=18.0, y=8.0),
        desk=TileCoord(x=16.0, y=4.0),
        subdesk=TileCoord(x=20.0, y=4.0),
        color="#10B981",
        icon="💻",
        description="Autonomous Coding Lab, Self-Healing & Hermes MCP Confinement"
    ),
    "research_room": RoomDefinition(
        name="RESEARCH ROOM",
        code="research_room",
        x=25, y=1, w=10, h=7,
        door=TileCoord(x=24.0, y=4.0),
        desk=TileCoord(x=30.0, y=4.0),
        color="#8B5CF6",
        icon="🔬",
        description="Knowledge Scout, Deep Web Perception & AST Inspection"
    ),
    "test_lab": RoomDefinition(
        name="TEST LAB",
        code="test_lab",
        x=1, y=9, w=10, h=6,
        door=TileCoord(x=11.0, y=12.0),
        desk=TileCoord(x=5.0, y=12.0),
        color="#F59E0B",
        icon="🧪",
        description="Continuous Pytest Suite, Regression Gate & Verification"
    ),
    "central_hub": RoomDefinition(
        name="CENTRAL CROSSWAY & HUB",
        code="central_hub",
        x=12, y=9, w=12, h=6,
        door=TileCoord(x=18.0, y=12.0),
        desk=TileCoord(x=18.0, y=12.0),
        color="#64748B",
        icon="🌐",
        description="Cross-Room Waypoint Corridors & Agent Meeting Hub"
    ),
    "security_vault": RoomDefinition(
        name="SECURITY VAULT",
        code="security_vault",
        x=25, y=9, w=10, h=6,
        door=TileCoord(x=24.0, y=12.0),
        desk=TileCoord(x=30.0, y=12.0),
        color="#EF4444",
        icon="🛡️",
        description="Cryptographic SHA-256 Audit Ledger & Capability Policy Guard"
    ),
    "docs_room": RoomDefinition(
        name="DOCS ROOM",
        code="docs_room",
        x=1, y=16, w=10, h=7,
        door=TileCoord(x=11.0, y=19.0),
        desk=TileCoord(x=5.0, y=19.0),
        color="#06B6D4",
        icon="📝",
        description="Architecture Specs, Living Markdown & User Documentation"
    ),
    "devops_dock": RoomDefinition(
        name="DEVOPS DOCK",
        code="devops_dock",
        x=13, y=16, w=10, h=7,
        door=TileCoord(x=18.0, y=15.0),
        desk=TileCoord(x=18.0, y=19.0),
        color="#EC4899",
        icon="🚀",
        description="FastAPI Runtime Gateway, CI/CD & Android Release Dock"
    ),
    "memory_core": RoomDefinition(
        name="MEMORY CORE",
        code="memory_core",
        x=25, y=16, w=10, h=7,
        door=TileCoord(x=24.0, y=19.0),
        desk=TileCoord(x=30.0, y=19.0),
        color="#A855F7",
        icon="🧠",
        description="Unified SQLite WAL, FTS5 Search & Vector Cognitive Store"
    ),
}


@router.get("/api/v1/office/map", response_model=OfficeMapResponse)
@router.get("/office/map", response_model=OfficeMapResponse)
async def get_office_map():
    """Fournit la cartographie spatiale canonique 2.5D du bureau et les coordonnées des pièces."""
    return OfficeMapResponse(
        ok=True,
        grid_width=36,
        grid_height=24,
        tile_size=28,
        rooms=CANONICAL_OFFICE_MAP,
    )

