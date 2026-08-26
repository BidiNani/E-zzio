"""E-ZZIO Core — Antigravity Federated Provider Implementation (Phase 4C).

Adapter implementing BaseFederatedProvider using AntigravityClient.
"""

from __future__ import annotations

import uuid
from pathlib import Path
from core.cognition.model_federation.base_provider import (
    BaseFederatedProvider,
    FederatedTaskRequest,
    FederatedTaskResult,
    ProviderDomain,
)
from core.cognition.antigravity.client import AntigravityClient
from core.cognition.antigravity.capabilities import (
    AntigravityAgentRequest,
    AntigravityExecutionMode,
    AntigravityOutputFormat,
    AntigravityEffortLevel,
)


class AntigravityFederatedProvider(BaseFederatedProvider):
    def __init__(self, root_dir: Path = Path(r"G:\AI\E-zzio")):
        self.root_dir = root_dir
        self.client = AntigravityClient(root_dir=self.root_dir)

    @property
    def domain(self) -> ProviderDomain:
        return ProviderDomain.AGENT_ANTIGRAVITY

    def is_available(self) -> bool:
        """Returns True if agy binary is present and reachable."""
        try:
            return Path(self.client.agy_executable).exists() or bool(self.client._locate_agy_binary())
        except Exception:
            return False

    def execute(self, request: FederatedTaskRequest) -> FederatedTaskResult:
        workspace = request.context_metadata.get("workspace_path", self.root_dir)
        if isinstance(workspace, str):
            workspace = Path(workspace)

        mode = AntigravityExecutionMode.READ_ONLY_SANDBOX
        if request.context_metadata.get("allow_modifications", False):
            mode = AntigravityExecutionMode.ACCEPT_EDITS

        agent_req = AntigravityAgentRequest(
            task_id=request.task_id or f"AGY-TASK-{uuid.uuid4().hex[:8]}",
            task_type=request.task_type,
            prompt=request.prompt,
            workspace_path=workspace,
            mode=mode,
            output_format=AntigravityOutputFormat.JSON if request.context_metadata.get("require_json") else AntigravityOutputFormat.TEXT,
            effort=AntigravityEffortLevel.HIGH if "complex" in request.task_type else AntigravityEffortLevel.MEDIUM,
            timeout_seconds=request.timeout_seconds,
            dangerously_skip_permissions=request.context_metadata.get("auto_approve", False),
        )

        resp = self.client.execute_agent_task(agent_req)

        return FederatedTaskResult(
            task_id=resp.task_id,
            provider_domain=self.domain,
            model_name="antigravity_agent_federated",
            status=resp.status,
            content=resp.raw_output,
            structured_data=resp.structured_json,
            execution_duration_ms=resp.execution_time_ms,
            cost_estimate_usd=0.0,
        )
