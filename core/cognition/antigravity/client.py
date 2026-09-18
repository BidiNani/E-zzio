"""E-ZZIO Core — Antigravity Agent Client & Session Runtime (Phase 4B).

Asynchronous client orchestrating the execution of Antigravity CLI in non-interactive print/structured mode.
"""

from __future__ import annotations

import json
import logging
import os
import shutil
import subprocess
import time
from pathlib import Path

from core.cognition.antigravity.capabilities import (
    AntigravityAgentRequest,
    AntigravityAgentResponse,
    AntigravityExecutionMode,
    AntigravityOutputFormat,
    AntigravityPolicyViolationError,
)
from core.cognition.antigravity.desktop_bridge import (
    AntigravityDesktopBridge,
)
from core.cognition.antigravity.policy import AntigravityPolicyGovernor

logger = logging.getLogger(__name__)


class AntigravityClient:
    def __init__(self, root_dir: Path = Path(r"G:\AI\E-zzio")):
        self.root_dir = root_dir
        self.policy_governor = AntigravityPolicyGovernor(root_dir=self.root_dir)
        self.agy_executable = self._locate_agy_binary()
        self.desktop_bridge = AntigravityDesktopBridge(
            bridge_dir=self.root_dir
            / "core"
            / "cognition"
            / "antigravity"
            / "desktop_bridge"
        )

    def _locate_agy_binary(self) -> str:
        """Locates the agy CLI binary on host PATH or standard installation directory."""
        found = shutil.which("agy")
        if found:
            return found

        standard_path = Path(os.environ.get("LOCALAPPDATA", "")) / "agy" / "bin" / "agy.exe"
        if standard_path.exists():
            return str(standard_path)

        return "agy"

    def desktop_available(self) -> bool:
        """Returns True when the local Antigravity Desktop bridge is installed."""
        try:
            return self.desktop_bridge.available
        except Exception:
            return False

    def desktop_execute_agent_task(
        self,
        request: AntigravityAgentRequest,
    ) -> AntigravityAgentResponse:
        """Submits a task to Antigravity Desktop without waiting for completion."""
        start_time = time.perf_counter()

        try:
            self.policy_governor.evaluate_request(request)
        except AntigravityPolicyViolationError as pve:
            return AntigravityAgentResponse(
                task_id=request.task_id,
                status="REJECTED_BY_POLICY",
                raw_output="",
                error_message=str(pve),
                execution_time_ms=(time.perf_counter() - start_time) * 1000,
            )

        try:
            created = self.desktop_bridge.request(
                "create_cascade",
            )

            if not created.get("ok"):
                return AntigravityAgentResponse(
                    task_id=request.task_id,
                    status="FAILED",
                    raw_output="",
                    error_message=str(
                        created.get(
                            "error",
                            "DESKTOP_CREATE_CASCADE_FAILED",
                        )
                    ),
                    execution_time_ms=(
                        time.perf_counter() - start_time
                    ) * 1000,
                    exit_code=-2,
                )

            cascade_id = created.get("cascadeId")

            if not cascade_id:
                return AntigravityAgentResponse(
                    task_id=request.task_id,
                    status="FAILED",
                    raw_output="",
                    error_message="DESKTOP_CASCADE_ID_MISSING",
                    execution_time_ms=(
                        time.perf_counter() - start_time
                    ) * 1000,
                    exit_code=-2,
                )

            send_kwargs = {
                "cascadeId": cascade_id,
                "text": request.prompt,
            }

            if request.model_override:
                send_kwargs["model"] = request.model_override

            sent = self.desktop_bridge.request(
                "send_message",
                **send_kwargs,
            )

            if not sent.get("ok"):
                self.desktop_bridge.request(
                    "dispose_cascade",
                    cascadeId=cascade_id,
                )

                return AntigravityAgentResponse(
                    task_id=request.task_id,
                    status="FAILED",
                    raw_output="",
                    error_message=str(
                        sent.get(
                            "error",
                            "DESKTOP_SEND_MESSAGE_FAILED",
                        )
                    ),
                    execution_time_ms=(
                        time.perf_counter() - start_time
                    ) * 1000,
                    exit_code=-2,
                )

            return AntigravityAgentResponse(
                task_id=request.task_id,
                status="DELEGATED",
                raw_output="",
                structured_json={
                    "backend": "antigravity_desktop",
                    "cascade_id": cascade_id,
                    "accepted": True,
                },
                execution_time_ms=(
                    time.perf_counter() - start_time
                ) * 1000,
                exit_code=0,
            )

        except Exception as exc:
            return AntigravityAgentResponse(
                task_id=request.task_id,
                status="FAILED",
                raw_output="",
                error_message=f"Desktop execution error: {exc}",
                execution_time_ms=(
                    time.perf_counter() - start_time
                ) * 1000,
                exit_code=-2,
            )

    def desktop_await_result(
        self,
        task_id: str,
        cascade_id: str,
        timeout_ms: int = 600000,
    ) -> AntigravityAgentResponse:
        """Wait for a previously delegated Desktop cascade without resubmitting it."""
        started = time.perf_counter()

        try:
            result = self.desktop_bridge.await_result(
                cascade_id=cascade_id,
                timeout_ms=timeout_ms,
            )

            elapsed_ms = (time.perf_counter() - started) * 1000.0

            if not result.get("ok"):
                return AntigravityAgentResponse(
                    task_id=task_id,
                    status="FAILED",
                    raw_output="",
                    structured_json=result,
                    execution_time_ms=elapsed_ms,
                    exit_code=1,
                    error_message=result.get("error", "DESKTOP_AWAIT_RESULT_FAILED"),
                )

            classification = self.desktop_bridge.classify_history_detail(
                cascade_id
            )

            structured = dict(result)
            structured["classification"] = classification.get(
                "classification",
                "UNKNOWN",
            )

            if classification.get("classification") == "BLOCKED_BY_EXTERNAL_QUOTA":
                structured["reason"] = classification.get(
                    "reason",
                    "ANTIGRAVITY_QUOTA_EXHAUSTED",
                )

                return AntigravityAgentResponse(
                    task_id=task_id,
                    status="BLOCKED_BY_EXTERNAL_QUOTA",
                    raw_output="",
                    structured_json=structured,
                    execution_time_ms=elapsed_ms,
                    exit_code=1,
                    error_message=structured["reason"],
                )

            final_status = str(result.get("status", "")).upper()

            if final_status == "IDLE" and result.get("text"):
                return AntigravityAgentResponse(
                    task_id=task_id,
                    status="SUCCESS",
                    raw_output=str(result.get("text", "")),
                    structured_json=structured,
                    execution_time_ms=elapsed_ms,
                    exit_code=0,
                )

            if classification.get("classification") == "FAILED":
                return AntigravityAgentResponse(
                    task_id=task_id,
                    status="FAILED",
                    raw_output="",
                    structured_json=structured,
                    execution_time_ms=elapsed_ms,
                    exit_code=1,
                    error_message="DESKTOP_CASCADE_FAILED",
                )

            return AntigravityAgentResponse(
                task_id=task_id,
                status="FAILED",
                raw_output="",
                structured_json=structured,
                execution_time_ms=elapsed_ms,
                exit_code=1,
                error_message="DESKTOP_RESULT_UNRESOLVED",
            )

        except Exception as exc:
            elapsed_ms = (time.perf_counter() - started) * 1000.0

            return AntigravityAgentResponse(
                task_id=task_id,
                status="FAILED",
                raw_output="",
                execution_time_ms=elapsed_ms,
                exit_code=1,
                error_message=f"Desktop result error: {exc}",
            )

    def execute_agent_task(self, request: AntigravityAgentRequest) -> AntigravityAgentResponse:
        """Synchronously executes an Antigravity task with strict timeout and policy validation."""
        start_time = time.perf_counter()

        # 1. Policy Evaluation (Fail-Closed)
        try:
            self.policy_governor.evaluate_request(request)
        except AntigravityPolicyViolationError as pve:
            return AntigravityAgentResponse(
                task_id=request.task_id,
                status="REJECTED_BY_POLICY",
                raw_output="",
                error_message=str(pve),
                execution_time_ms=(time.perf_counter() - start_time) * 1000,
            )

        # 2. Build CLI Command
        cmd = [
            self.agy_executable,
            "--print",
            request.prompt,
            "--output-format",
            request.output_format.value,
            "--effort",
            request.effort.value,
        ]

        if request.model_override:
            cmd.extend(["--model", request.model_override])

        if request.mode == AntigravityExecutionMode.READ_ONLY_SANDBOX:
            cmd.append("--sandbox")
        elif request.mode == AntigravityExecutionMode.ACCEPT_EDITS:
            cmd.extend(["--mode", "accept-edits"])
        elif request.mode == AntigravityExecutionMode.PLAN_ONLY:
            cmd.extend(["--mode", "plan"])

        if request.dangerously_skip_permissions:
            cmd.append("--dangerously-skip-permissions")

        # 3. Process Execution
        try:
            res = subprocess.run(
                cmd,
                cwd=str(request.workspace_path),
                capture_output=True,
                text=True,
                timeout=request.timeout_seconds,
                encoding="utf-8",
                errors="replace",
            )
            elapsed_ms = (time.perf_counter() - start_time) * 1000
            raw_out = res.stdout.strip() if res.stdout else res.stderr.strip()

            structured = None
            if request.output_format == AntigravityOutputFormat.JSON and res.returncode == 0:
                try:
                    structured = json.loads(raw_out)
                except Exception:
                    pass

            return AntigravityAgentResponse(
                task_id=request.task_id,
                status="SUCCESS" if res.returncode == 0 else "FAILED",
                raw_output=raw_out,
                structured_json=structured,
                execution_time_ms=elapsed_ms,
                exit_code=res.returncode,
                error_message=res.stderr.strip() if res.returncode != 0 else None,
            )

        except subprocess.TimeoutExpired:
            return AntigravityAgentResponse(
                task_id=request.task_id,
                status="TIMEOUT",
                raw_output="",
                error_message=f"Antigravity agent execution timed out after {request.timeout_seconds}s.",
                execution_time_ms=(time.perf_counter() - start_time) * 1000,
                exit_code=-1,
            )
        except Exception as exc:
            return AntigravityAgentResponse(
                task_id=request.task_id,
                status="FAILED",
                raw_output="",
                error_message=f"Execution error: {exc}",
                execution_time_ms=(time.perf_counter() - start_time) * 1000,
                exit_code=-2,
            )
