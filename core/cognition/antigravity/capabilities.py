"""E-ZZIO Core — Antigravity Federated Agent Capabilities & Contracts (Phase 4A/4B).

Defines strongly-typed interfaces for delegating agentic tasks from E-ZZIO to Antigravity CLI/Agent runtime,
with strict capability boundaries, sandboxing levels, output schemas, and security envelopes.
"""

from __future__ import annotations

import enum
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any


class AntigravityExecutionMode(str, enum.Enum):
    PLAN_ONLY = "plan"
    ACCEPT_EDITS = "accept-edits"
    READ_ONLY_SANDBOX = "read-only-sandbox"


class AntigravityOutputFormat(str, enum.Enum):
    TEXT = "text"
    JSON = "json"
    STREAM_JSON = "stream-json"


class AntigravityEffortLevel(str, enum.Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


@dataclass
class AntigravityAgentRequest:
    task_id: str
    task_type: str
    prompt: str
    workspace_path: Path
    mode: AntigravityExecutionMode = AntigravityExecutionMode.READ_ONLY_SANDBOX
    output_format: AntigravityOutputFormat = AntigravityOutputFormat.JSON
    effort: AntigravityEffortLevel = AntigravityEffortLevel.MEDIUM
    model_override: str | None = None
    timeout_seconds: int = 120
    dangerously_skip_permissions: bool = False
    context_metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class AntigravityAgentResponse:
    task_id: str
    status: str  # "SUCCESS", "FAILED", "REJECTED_BY_POLICY", "TIMEOUT"
    raw_output: str
    structured_json: dict[str, Any] | None = None
    execution_time_ms: float = 0.0
    exit_code: int = 0
    error_message: str | None = None
    timestamp_utc: str = field(default_factory=lambda: datetime.now(UTC).isoformat())


class AntigravityPolicyViolationError(Exception):
    """Raised when an Antigravity delegation request violates E-ZZIO safety boundaries."""

    pass
