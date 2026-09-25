"""E-ZZIO Governed Hermes Worker Profiles.

Provides governed, multi-capability execution profiles for external Hermes workers:
- Full capability model: Tools, Skills, Plugins, MCP, Network, Memory, Delegation
- Capability snapshot resolution (ResolvedWorkerCapabilities)
- Strict escalation prevention: profile authority resides with E-ZZIO Master
- Canonical profiles:
  * context_reader / reader (zero tools, context fed, read-only)
  * context_auditor / auditor (zero tools, context fed, read-only)
  * researcher (web, search, skills, read-only, network=WEB)
  * analyst (web, search, skills, multi-source analysis, read-only, network=WEB)
  * operator (file, terminal, skills in bounded isolated workspace only)
  * coder (DEFERRED - core/coding/coder_worker.py is active backend)
  * tester (DEFERRED - governed by E-ZZIO test runner)
"""
from __future__ import annotations

import json
import logging
import os
import re
from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any

from core.agent.agent_guard import AgentPolicyGuard
from core.security.audit_ledger import AuditLedger

logger = logging.getLogger("HermesWorkerProfiles")


class NetworkPolicy(StrEnum):
    """Network access policy levels for governed workers."""
    DENY = "deny"
    LOOPBACK_ONLY = "loopback_only"
    WEB = "web"
    WEB_AND_MCP = "web_and_mcp"
    FULL_EXTERNAL = "full_external"


class WorkerProfileType(StrEnum):
    """Canonical worker profile types."""
    CONTEXT_READER = "context_reader"
    CONTEXT_AUDITOR = "context_auditor"
    READER = "reader"
    AUDITOR = "auditor"
    RESEARCHER = "researcher"
    ANALYST = "analyst"
    OPERATOR = "operator"
    CODER = "coder"    # DEFERRED
    TESTER = "tester"  # DEFERRED


# Direct mapping of Hermes toolsets to their underlying tools
# Derived from local Hermes v0.21.5+ (G:\Hermes\hermes-agent\toolsets.py)
HERMES_TOOLSETS_MAP: dict[str, list[str]] = {
    "web": ["web_search", "web_extract"],
    "skills": ["skills_list", "skill_view", "skill_manage"],
    "file": ["read_file", "write_file", "patch", "search_files"],
    "terminal": ["terminal", "process_manage"],
    "browser": [
        "browser_navigate", "browser_snapshot", "browser_click", "browser_type",
        "browser_scroll", "browser_back", "browser_press", "browser_get_images",
        "browser_vision", "browser_console", "browser_cdp", "browser_dialog",
        "browser_vault_list", "browser_vault_unlock", "browser_vault_fill",
        "browser_vault_save_login", "browser_vault_enter_code", "browser_exec",
    ],
    "memory": ["memory"],
    "code_execution": ["execute_code"],
    "delegation": ["delegate_task"],
    "session_search": ["session_search"],
}


def resolve_tools_for_toolsets(toolsets: tuple[str, ...]) -> tuple[str, ...]:
    """Resolves an iterable of Hermes toolsets into concrete tool names."""
    tools: list[str] = []
    for ts in toolsets:
        found = HERMES_TOOLSETS_MAP.get(ts, [])
        for tool_name in found:
            if tool_name not in tools:
                tools.append(tool_name)
    return tuple(sorted(tools))


@dataclass(frozen=True)
class ResolvedWorkerCapabilities:
    """Auditable capability snapshot resolved from a WorkerProfile and runtime state."""
    profile_name: str
    toolsets: tuple[str, ...]
    tools: tuple[str, ...]
    skills: tuple[str, ...]
    plugins: tuple[str, ...]
    mcp_servers: tuple[str, ...]
    mcp_tools: tuple[str, ...]
    network: str
    filesystem: str
    memory: str
    delegation: bool
    model_role_hint: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "profile_name": self.profile_name,
            "toolsets": list(self.toolsets),
            "tools": list(self.tools),
            "skills": list(self.skills),
            "plugins": list(self.plugins),
            "mcp_servers": list(self.mcp_servers),
            "mcp_tools": list(self.mcp_tools),
            "network": self.network,
            "filesystem": self.filesystem,
            "memory": self.memory,
            "delegation": self.delegation,
            "model_role_hint": self.model_role_hint,
        }


@dataclass(frozen=True)
class WorkerProfile:
    """Immutable governance profile for a governed Hermes external worker."""
    name: WorkerProfileType | str
    purpose: str = ""
    hermes_toolsets: tuple[str, ...] = ()
    skills: tuple[str, ...] = ()
    plugins: tuple[str, ...] = ()
    mcp_servers: tuple[str, ...] = ()
    mcp_tools: tuple[str, ...] = ()
    read_only: bool = True
    filesystem_scope: str | None = None
    network_policy: NetworkPolicy = NetworkPolicy.DENY
    memory_policy: str = "disabled"
    delegation_enabled: bool = False
    safe_mode: bool = True
    default_timeout_sec: int = 60
    max_turns: int = 10
    max_tool_calls: int = 20
    max_output: int = 32000
    model_role_hint: str | None = None
    role_description: str = ""
    status: str = "PROVEN"

    @property
    def timeout_seconds(self) -> int:
        return self.default_timeout_sec

    @property
    def memory_enabled(self) -> bool:
        return self.memory_policy != "disabled"

    @property
    def network_enabled(self) -> bool:
        return self.network_policy != NetworkPolicy.DENY

    def resolve_capabilities(self, workspace_root: str = r"G:\AI\E-zzio") -> ResolvedWorkerCapabilities:
        """Produces a deterministic, auditable capability snapshot."""
        resolved_tools = resolve_tools_for_toolsets(self.hermes_toolsets)
        return ResolvedWorkerCapabilities(
            profile_name=str(self.name),
            toolsets=self.hermes_toolsets,
            tools=resolved_tools,
            skills=self.skills,
            plugins=self.plugins,
            mcp_servers=self.mcp_servers,
            mcp_tools=self.mcp_tools,
            network=self.network_policy.value if hasattr(self.network_policy, "value") else str(self.network_policy),
            filesystem=self.filesystem_scope or ("read_only" if self.read_only else "bounded_workspace"),
            memory=self.memory_policy,
            delegation=self.delegation_enabled,
            model_role_hint=self.model_role_hint,
        )


# ==============================================================================
# CANONICAL WORKER PROFILES
# ==============================================================================

# 1. Context Reader (Zero Hermes Tools, E-ZZIO governed context)
CONTEXT_ONLY_READER = WorkerProfile(
    name=WorkerProfileType.READER,
    purpose="Pure cognitive reading, semantic analysis, and synthesis of context-provided files.",
    hermes_toolsets=(),
    skills=(),
    plugins=(),
    mcp_servers=(),
    read_only=True,
    filesystem_scope="none",
    network_policy=NetworkPolicy.DENY,
    memory_policy="disabled",
    delegation_enabled=False,
    safe_mode=True,
    default_timeout_sec=45,
    max_turns=1,
    role_description="Pure cognitive reading and understanding of context-provided files.",
    status="PROVEN",
)

# 2. Context Auditor (Zero Hermes Tools, static security reasoning)
CONTEXT_ONLY_AUDITOR = WorkerProfile(
    name=WorkerProfileType.AUDITOR,
    purpose="Forensic static audit, compliance checking, and vulnerability analysis of context-provided files.",
    hermes_toolsets=(),
    skills=(),
    plugins=(),
    mcp_servers=(),
    read_only=True,
    filesystem_scope="none",
    network_policy=NetworkPolicy.DENY,
    memory_policy="disabled",
    delegation_enabled=False,
    safe_mode=True,
    default_timeout_sec=60,
    max_turns=1,
    role_description="Forensic static audit, compliance checking, and vulnerability analysis of context-provided files.",
    status="PROVEN",
)

# 3. Researcher (Rich Worker: Web search, extraction, and validated skills)
RESEARCHER_PROFILE = WorkerProfile(
    name=WorkerProfileType.RESEARCHER,
    purpose="Autonomous research, web exploration, documentation gathering, and knowledge synthesis.",
    hermes_toolsets=("web", "skills"),
    skills=("grounded-citations",),
    plugins=(),
    mcp_servers=(),
    read_only=True,
    filesystem_scope="none",
    network_policy=NetworkPolicy.WEB,
    memory_policy="disabled",
    delegation_enabled=False,
    safe_mode=False,
    default_timeout_sec=60,
    max_turns=8,
    max_tool_calls=15,
    role_description="Autonomous web research, fact gathering, and cited synthesis.",
    status="PROVEN",
)

# 4. Analyst (Rich Worker: Deep reasoning, correlation, web & skill access, strictly read-only)
ANALYST_PROFILE = WorkerProfile(
    name=WorkerProfileType.ANALYST,
    purpose="Multi-source correlation, advanced document analysis, architecture review, and synthesis.",
    hermes_toolsets=("web", "skills"),
    skills=("grounded-citations",),
    plugins=(),
    mcp_servers=(),
    read_only=True,
    filesystem_scope="none",
    network_policy=NetworkPolicy.WEB,
    memory_policy="disabled",
    delegation_enabled=False,
    safe_mode=False,
    default_timeout_sec=60,
    max_turns=8,
    max_tool_calls=15,
    role_description="Multi-source analysis and architectural synthesis.",
    status="PROVEN",
)

# 5. Operator (Operational Worker: Bounded local workspace operations, file & terminal)
OPERATOR_PROFILE = WorkerProfile(
    name=WorkerProfileType.OPERATOR,
    purpose="Bounded local workspace maintenance, file creation/inspection, and controlled terminal operations.",
    hermes_toolsets=("file", "terminal", "skills"),
    skills=(),
    plugins=(),
    mcp_servers=(),
    read_only=False,
    filesystem_scope="isolated_workspace",
    network_policy=NetworkPolicy.LOOPBACK_ONLY,
    memory_policy="disabled",
    delegation_enabled=False,
    safe_mode=False,
    default_timeout_sec=60,
    max_turns=10,
    max_tool_calls=25,
    role_description="Bounded operational file and terminal maintenance in isolated workspace.",
    status="PROVEN",
)

# 6. Coder (DEFERRED: core/coding/coder_worker.py is active backend)
CODER_PROFILE = WorkerProfile(
    name=WorkerProfileType.CODER,
    purpose="Autonomous code implementation and refactoring (DEFERRED).",
    hermes_toolsets=(),
    read_only=True,
    status="DEFERRED",
)

# 7. Tester (DEFERRED: governed by E-ZZIO test runner)
TESTER_PROFILE = WorkerProfile(
    name=WorkerProfileType.TESTER,
    purpose="Governed test execution and failure diagnostic (DEFERRED).",
    hermes_toolsets=(),
    read_only=True,
    status="DEFERRED",
)


# Canonical Profile Registry
WORKER_PROFILES: dict[str, WorkerProfile] = {
    "context_reader": CONTEXT_ONLY_READER,
    "context_only_reader": CONTEXT_ONLY_READER,
    "reader": CONTEXT_ONLY_READER,
    "context_auditor": CONTEXT_ONLY_AUDITOR,
    "context_only_auditor": CONTEXT_ONLY_AUDITOR,
    "auditor": CONTEXT_ONLY_AUDITOR,
    "researcher": RESEARCHER_PROFILE,
    "analyst": ANALYST_PROFILE,
    "operator": OPERATOR_PROFILE,
    "coder": CODER_PROFILE,
    "tester": TESTER_PROFILE,
}


def resolve_profile(name_or_profile: str | WorkerProfile) -> WorkerProfile:
    """Deterministically resolves a WorkerProfile from a name or returns the existing profile.

    Strict Escalation Protection:
    - Never elevates capabilities based on user prompt or task payload.
    - If unknown profile, raises ValueError (Fail-Closed).
    """
    if isinstance(name_or_profile, WorkerProfile):
        return name_or_profile
    key = str(name_or_profile).strip().lower()
    if key in WORKER_PROFILES:
        return WORKER_PROFILES[key]
    raise ValueError(f"[POLICY_DENIED] Unknown or unauthorized worker profile: '{name_or_profile}'")


def is_capability_allowed(profile: WorkerProfile, capability: str) -> bool:
    """Checks whether a specific tool or system capability is allowed under the given profile."""
    cap = capability.lower().strip()
    caps = profile.resolve_capabilities()

    if cap in ("terminal", "process_manage"):
        return "terminal" in caps.toolsets
    if cap in ("write_file", "patch"):
        return not profile.read_only and "file" in caps.toolsets
    if cap in ("read_file", "search_files"):
        return "file" in caps.toolsets
    if cap in ("web_search", "web_extract"):
        return "web" in caps.toolsets
    if cap in ("skills_list", "skill_view", "skill_manage"):
        return "skills" in caps.toolsets
    if cap == "plugin_install":
        return False  # Strictly forbidden to all workers
    if cap == "mcp_arbitrary":
        return False  # Strictly forbidden to all workers
    if cap == "delegation":
        return profile.delegation_enabled
    if cap == "memory":
        return profile.memory_enabled

    return cap in caps.tools or cap in caps.toolsets


# ==============================================================================
# CONTEXT-PACK INFRASTRUCTURE (Governed Context Feeding)
# ==============================================================================

@dataclass(frozen=True)
class ContextFile:
    """Represents a bounded, pre-read file provided into context."""
    path: str
    content: str
    size_bytes: int = 0


@dataclass(frozen=True)
class ContextPack:
    """Bounded, policy-verified context package passed to a worker."""
    task_id: str
    objective: str
    files: tuple[ContextFile, ...]
    metadata: dict[str, Any] = field(default_factory=dict)


def build_context_pack(
    task_id: str,
    objective: str,
    file_paths: list[str],
    workspace_root: str = r"G:\AI\E-zzio",
    policy_guard: AgentPolicyGuard | None = None,
    audit_ledger: AuditLedger | None = None,
    metadata: dict[str, Any] | None = None,
) -> ContextPack:
    """Constructs a policy-verified ContextPack by reading allowed files.

    Fail-closed:
    - Any attempt to read out-of-workspace files raises PermissionError.
    - Any attempt to read protected files (.env, .git, tokens, etc.) raises PermissionError.
    - Audit event CONTEXT_PACK_CREATED is recorded.
    """
    guard = policy_guard or AgentPolicyGuard(workspace_root)
    collected_files: list[ContextFile] = []

    for rel_or_abs in file_paths:
        clean_path = rel_or_abs.strip()
        if not clean_path:
            continue

        # Evaluate intent through AgentPolicyGuard
        allowed, reason = guard.evaluate_intent("read_file", {"path": clean_path})
        if not allowed:
            err_msg = f"[POLICY_DENIED] Access denied for '{clean_path}': {reason}"
            logger.warning("[build_context_pack DENIED] %s", err_msg)
            if audit_ledger:
                audit_ledger.record_event(
                    actor="ezzio-policy-guard",
                    action="CONTEXT_PACK_POLICY_DENIED",
                    payload={"task_id": task_id, "path": clean_path, "reason": reason},
                    status="DENIED",
                )
            raise PermissionError(err_msg)

        # Strict read protection for secrets, credentials, and sensitive files
        norm_path = os.path.normpath(clean_path).lower()
        path_parts = norm_path.replace("\\", "/").split("/")
        is_sensitive = (
            ".env" in norm_path
            or ".git" in norm_path
            or "secrets" in path_parts
            or any(part.startswith(".env") for part in path_parts)
            or any(frag in norm_path for frag in [".key", ".pem", "id_rsa"])
        )
        if is_sensitive:
            reason = "Reading secrets, credentials, or metadata files into context is prohibited"
            err_msg = f"[POLICY_DENIED] Access denied for '{clean_path}': {reason}"
            logger.warning("[build_context_pack DENIED] %s", err_msg)
            if audit_ledger:
                audit_ledger.record_event(
                    actor="ezzio-policy-guard",
                    action="CONTEXT_PACK_POLICY_DENIED",
                    payload={"task_id": task_id, "path": clean_path, "reason": reason},
                    status="DENIED",
                )
            raise PermissionError(err_msg)

        # Resolve full path
        full_path = (
            clean_path
            if os.path.isabs(clean_path)
            else os.path.join(workspace_root, clean_path)
        )

        if not os.path.exists(full_path):
            logger.warning("[build_context_pack] File not found: %s", full_path)
            continue

        try:
            with open(full_path, encoding="utf-8", errors="replace") as f:
                content = f.read()
            rel_name = os.path.relpath(full_path, workspace_root)
            collected_files.append(ContextFile(path=rel_name, content=content, size_bytes=len(content.encode("utf-8"))))
        except Exception as read_err:
            logger.error("[build_context_pack] Failed to read %s: %s", full_path, read_err)
            raise

    pack = ContextPack(
        task_id=task_id,
        objective=objective,
        files=tuple(collected_files),
        metadata=metadata or {},
    )

    if audit_ledger:
        audit_ledger.record_event(
            actor="ezzio-master",
            action="CONTEXT_PACK_CREATED",
            payload={
                "task_id": task_id,
                "file_count": len(pack.files),
                "files": [f.path for f in pack.files],
                "objective": objective[:200],
            },
            status="SUCCESS",
        )

    return pack


def render_context_prompt(
    context_pack: ContextPack,
    profile: WorkerProfile,
    extra_instructions: str = "",
) -> str:
    """Renders a bounded prompt including the context files and role constraints."""
    role_title = str(profile.name).upper()
    sections = [
        f"### WORKER ROLE: {role_title}",
        f"Description: {profile.role_description or profile.purpose}",
        "\nIMPORTANT OPERATIONAL INSTRUCTIONS:",
        "1. You are operating as a PURE COGNITIVE WORKER with ZERO tools." if not profile.hermes_toolsets else f"1. You are operating with authorized toolsets: {', '.join(profile.hermes_toolsets)}.",
        "2. You DO NOT have access to unauthorized filesystem mutation, processes, or arbitrary plugins.",
        "3. You MUST analyze ONLY the bounded context and authorized inputs.",
        "4. Your final output MUST be valid JSON conforming to the requested schema.\n",
        f"### OBJECTIVE\n{context_pack.objective}\n",
        "### CONTEXT FILES",
    ]

    for cf in context_pack.files:
        sections.append(f"--- BEGIN FILE: {cf.path} ---")
        sections.append(cf.content)
        sections.append(f"--- END FILE: {cf.path} ---\n")

    if extra_instructions:
        sections.append(f"### ADDITIONAL INSTRUCTIONS\n{extra_instructions}\n")

    sections.append(
        "### REQUIRED OUTPUT FORMAT (STRICT JSON ONLY)\n"
        "Produce your final response strictly as valid JSON without markdown wrapping or commentary:\n"
        "{\n"
        '  "status": "SUCCESS",\n'
        '  "summary": "Brief executive summary of findings",\n'
        '  "findings": ["Point 1", "Point 2"],\n'
        '  "evidence": ["Evidence reference 1"],\n'
        '  "unknowns": ["Any unverified elements"],\n'
        '  "confidence": 0.95\n'
        "}"
    )

    return "\n".join(sections)


def parse_structured_result(raw_text: str) -> dict[str, Any]:
    """Parses and normalizes the structured JSON result from worker response."""
    clean_text = raw_text.strip()
    match = re.search(r"\{[\s\S]*\}", clean_text)
    if match:
        try:
            data = json.loads(match.group(0))
            if isinstance(data, dict):
                return {
                    "status": data.get("status", "SUCCESS"),
                    "summary": data.get("summary", clean_text[:200]),
                    "findings": data.get("findings", []),
                    "evidence": data.get("evidence", []),
                    "unknowns": data.get("unknowns", []),
                    "confidence": float(data.get("confidence", 1.0)),
                }
        except Exception:
            pass

    return {
        "status": "SUCCESS" if clean_text else "FAILED",
        "summary": clean_text[:300] if clean_text else "No output produced.",
        "findings": [clean_text] if clean_text else [],
        "evidence": [],
        "unknowns": [],
        "confidence": 0.8 if clean_text else 0.0,
    }
