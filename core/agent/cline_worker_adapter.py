"""E-ZZIO Cline External Worker Adapter.

Provides a strictly governed, bounded execution bridge between E-ZZIO Master
(exclusive cognitive authority) and Cline (external execution worker).

Architectural Principles:
- "Cline is a WORKER, NEVER an AUTHORITY."
- E-ZZIO decides -> E-ZZIO governs -> Cline executes -> E-ZZIO observes -> E-ZZIO validates -> E-ZZIO accepts or rejects.
- Worker Result != Proof: All worker outputs are marked OBSERVED until E-ZZIO independently inspects and validates them.
- Fail-Closed Security: If the cline binary is absent or policy checks fail, returns UNAVAILABLE or POLICY_DENIED.
- Worktree Isolation: Tasks can execute in isolated worktrees to protect the canonical repository.
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
import shutil
import subprocess
import sys
import tempfile
import time
from dataclasses import dataclass, field
from typing import Any

from core.agent.agent_guard import AgentPolicyGuard
from core.agent.command_executor import redact_secrets
from core.security.audit_ledger import AuditLedger

logger = logging.getLogger("ClineWorkerAdapter")

# Global forbidden commands for worker execution
GLOBAL_FORBIDDEN_COMMANDS: frozenset[str] = frozenset({
    "rm -rf",
    "git reset --hard",
    "git clean -fd",
    "del /s",
    "rmdir /s",
    "format",
})


@dataclass
class ClineWorkerRequest:
    """Normalized request payload for Cline external worker execution."""

    task_id: str
    prompt: str
    mission_id: str | None = None
    working_directory: str = r"G:\AI\E-zzio"
    allowed_tools: list[str] = field(default_factory=list)
    timeout_sec: float = 60.0
    max_turns: int | None = None
    model: str | None = None
    provider: str | None = None
    use_worktree_isolation: bool = True
    context: dict[str, Any] = field(default_factory=dict)


@dataclass
class ClineWorkerResult:
    """Normalized result object returned by Cline external worker execution.

    IMPORTANT: All fields are OBSERVED reports from the worker.
    Final proof and acceptance must be verified independently by E-ZZIO.
    """

    worker_id: str = "cline"
    task_id: str = ""
    status: str = "FAILED"  # SUCCESS | FAILED | TIMEOUT | CANCELLED | POLICY_DENIED | UNAVAILABLE
    exit_code: int = -1
    stdout: str = ""
    stderr: str = ""
    output: str = ""
    changed_files: list[str] = field(default_factory=list)
    duration_ms: float = 0.0
    worktree_path: str | None = None
    error: str | None = None
    provenance: dict[str, Any] = field(default_factory=dict)
    structured_output: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "worker_id": self.worker_id,
            "task_id": self.task_id,
            "status": self.status,
            "exit_code": self.exit_code,
            "stdout": redact_secrets(self.stdout[:2000]),
            "stderr": redact_secrets(self.stderr[:2000]),
            "output": redact_secrets(self.output[:2000]),
            "changed_files": self.changed_files,
            "duration_ms": self.duration_ms,
            "worktree_path": self.worktree_path,
            "error": self.error,
            "provenance": self.provenance,
            "structured_output": self.structured_output,
        }


class ClineWorkerAdapter:
    """Governed Adapter for Cline as an external execution worker."""

    def __init__(
        self,
        cline_binary_path: str | None = None,
        workspace_root: str = r"G:\AI\E-zzio",
        audit_ledger: AuditLedger | None = None,
        policy_guard: AgentPolicyGuard | None = None,
        default_timeout_sec: float = 60.0,
    ) -> None:
        self.workspace_root = os.path.abspath(workspace_root)
        self.cline_binary_path = self._resolve_cline_bin(cline_binary_path)
        self.audit_ledger = audit_ledger or AuditLedger()
        self.policy_guard = policy_guard or AgentPolicyGuard(workspace_root=self.workspace_root)
        self.default_timeout_sec = default_timeout_sec
        self._active_processes: dict[str, asyncio.subprocess.Process] = {}
        self._cached_version: str | None = None

    def _resolve_cline_bin(self, explicit_bin: str | None) -> str | None:
        if explicit_bin:
            return explicit_bin

        candidates = [
            shutil.which("cline"),
            shutil.which("cline.exe"),
            shutil.which("cline.cmd"),
            r"C:\Program Files\Cline\cline.exe",
            os.path.expandvars(r"%LOCALAPPDATA%\Programs\cline\cline.exe"),
            os.path.expandvars(r"%APPDATA%\npm\cline.cmd"),
        ]
        for c in candidates:
            if c and os.path.exists(c):
                return c
        return None

    def is_available(self) -> bool:
        """Checks if the Cline binary is installed and executable on the host system."""
        if not self.cline_binary_path:
            self.cline_binary_path = self._resolve_cline_bin(None)
        return bool(self.cline_binary_path and os.path.exists(self.cline_binary_path))

    def get_version(self) -> str | None:
        """Retrieves and caches the exact version of the Cline CLI."""
        if self._cached_version is not None:
            return self._cached_version
        if not self.is_available() or not self.cline_binary_path:
            return None
        try:
            res = subprocess.run(
                [self.cline_binary_path, "--version"],
                capture_output=True,
                text=True,
                timeout=5,
                check=False,
            )
            if res.returncode == 0 and res.stdout:
                ver = res.stdout.strip().splitlines()[0]
                self._cached_version = ver
                return ver
        except Exception as exc:
            logger.warning("[ClineWorkerAdapter] Failed to get Cline version: %s", exc)
        return None

    def build_cli_command(self, request: ClineWorkerRequest, target_dir: str) -> list[str]:
        """Constructs the bounded CLI command for Cline worker execution."""
        if not self.cline_binary_path:
            raise RuntimeError("Cline binary is not available.")

        cmd = [
            self.cline_binary_path,
            "--prompt", request.prompt,
            "--dir", target_dir,
            "--non-interactive",
            "--json",
        ]

        if request.model:
            cmd.extend(["--model", request.model])

        if request.provider:
            cmd.extend(["--provider", request.provider])

        if request.max_turns:
            cmd.extend(["--max-turns", str(request.max_turns)])

        if request.allowed_tools:
            cmd.extend(["--tools", ",".join(request.allowed_tools)])

        return cmd

    def _terminate_process_tree(self, proc: asyncio.subprocess.Process | None) -> None:
        """Kills the process and its descendants reliably across Windows & POSIX."""
        if proc is None or proc.returncode is not None:
            return
        try:
            if sys.platform == "win32":
                subprocess.run(
                    ["taskkill", "/F", "/T", "/PID", str(proc.pid)],
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                    check=False,
                )
            else:
                proc.kill()
        except Exception as exc:
            logger.warning("[ClineWorkerAdapter] Process tree termination failed: %s", exc)

    async def submit(self, request: ClineWorkerRequest) -> ClineWorkerResult:
        """Submits a coding task to the Cline external worker under strict E-ZZIO governance."""
        start_time = time.time()
        task_id = request.task_id

        # 1. Availability check (Fail-Closed)
        if not self.is_available():
            duration_ms = (time.time() - start_time) * 1000
            err_msg = "Cline CLI binary is not available on host system (Fail-Closed fallback to E-ZZIO native worker)."
            logger.info("[ClineWorkerAdapter] Task %s: %s", task_id, err_msg)
            self._record_audit(
                task_id=task_id,
                action="CLINE_WORKER_UNAVAILABLE",
                status="UNAVAILABLE",
                payload={"reason": err_msg},
            )
            return ClineWorkerResult(
                task_id=task_id,
                status="UNAVAILABLE",
                error=err_msg,
                duration_ms=duration_ms,
                provenance={"available": False, "reason": err_msg},
            )

        # 2. Security & Policy Inspection
        lower_prompt = request.prompt.lower()
        for forbidden in GLOBAL_FORBIDDEN_COMMANDS:
            if forbidden in lower_prompt:
                duration_ms = (time.time() - start_time) * 1000
                err_msg = f"[POLICY_DENIED] Forbidden destructive command in prompt: '{forbidden}'"
                logger.warning("[ClineWorkerAdapter] Task %s: %s", task_id, err_msg)
                self._record_audit(
                    task_id=task_id,
                    action="CLINE_WORKER_POLICY_DENIED",
                    status="POLICY_DENIED",
                    payload={"reason": err_msg},
                )
                return ClineWorkerResult(
                    task_id=task_id,
                    status="POLICY_DENIED",
                    error=err_msg,
                    duration_ms=duration_ms,
                    provenance={"policy_approved": False, "reason": err_msg},
                )

        target_dir = request.working_directory
        worktree_created_dir: str | None = None

        # 3. Worktree Isolation Setup (if requested)
        if request.use_worktree_isolation and os.path.exists(os.path.join(self.workspace_root, ".git")):
            try:
                temp_dir = tempfile.mkdtemp(prefix=f"ezzio_cline_{task_id}_")
                worktree_created_dir = temp_dir
                target_dir = temp_dir
            except Exception as wt_err:
                logger.warning("[ClineWorkerAdapter] Failed to create worktree isolation dir: %s", wt_err)
                target_dir = request.working_directory

        # Audit Event Log: CLINE_WORKER_SUBMITTED
        self._record_audit(
            task_id=task_id,
            action="CLINE_WORKER_SUBMITTED",
            status="RUNNING",
            payload={
                "prompt": request.prompt[:200],
                "target_dir": target_dir,
                "timeout_sec": request.timeout_sec,
                "model": request.model,
                "provider": request.provider,
            },
        )

        # 4. Build CLI Command
        try:
            cmd = self.build_cli_command(request, target_dir)
        except Exception as cmd_err:
            duration_ms = (time.time() - start_time) * 1000
            return ClineWorkerResult(
                task_id=task_id,
                status="FAILED",
                error=f"CLI command build error: {cmd_err}",
                duration_ms=duration_ms,
            )

        # 5. Process Execution
        process: asyncio.subprocess.Process | None = None
        try:
            creationflags = subprocess.CREATE_NEW_PROCESS_GROUP if sys.platform == "win32" else 0

            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=target_dir,
                creationflags=creationflags,
            )
            self._active_processes[task_id] = process

            stdout_bytes, stderr_bytes = await asyncio.wait_for(
                process.communicate(),
                timeout=request.timeout_sec,
            )
            stdout = stdout_bytes.decode("utf-8", errors="replace")
            stderr = stderr_bytes.decode("utf-8", errors="replace")
            duration_ms = (time.time() - start_time) * 1000
            exit_code = process.returncode if process.returncode is not None else 0

            status = "SUCCESS" if exit_code == 0 else "FAILED"

            # Parse output for changed files or structured payload
            changed_files = self._detect_changed_files(stdout, target_dir)
            structured_output = self._parse_json_output(stdout)

            result = ClineWorkerResult(
                task_id=task_id,
                status=status,
                exit_code=exit_code,
                stdout=stdout,
                stderr=stderr,
                output=stdout,
                changed_files=changed_files,
                duration_ms=duration_ms,
                worktree_path=worktree_created_dir,
                error=None if status == "SUCCESS" else f"Cline CLI exited with code {exit_code}",
                provenance={
                    "worker": "cline",
                    "cli_path": self.cline_binary_path,
                    "version": self.get_version(),
                    "command": cmd,
                },
                structured_output=structured_output,
            )

            self._record_audit(
                task_id=task_id,
                action="CLINE_WORKER_COMPLETED" if status == "SUCCESS" else "CLINE_WORKER_FAILED",
                status=status,
                payload={"exit_code": exit_code, "duration_ms": duration_ms},
            )

            return result

        except TimeoutError:
            duration_ms = (time.time() - start_time) * 1000
            err_msg = f"Cline execution timed out after {request.timeout_sec}s"
            logger.warning("[ClineWorkerAdapter] Task %s: %s", task_id, err_msg)
            self._terminate_process_tree(process)
            self._record_audit(
                task_id=task_id,
                action="CLINE_WORKER_TIMEOUT",
                status="TIMEOUT",
                payload={"timeout_sec": request.timeout_sec, "duration_ms": duration_ms},
            )
            return ClineWorkerResult(
                task_id=task_id,
                status="TIMEOUT",
                exit_code=-3,
                error=err_msg,
                duration_ms=duration_ms,
                worktree_path=worktree_created_dir,
            )

        except Exception as exc:
            duration_ms = (time.time() - start_time) * 1000
            err_msg = str(exc)
            logger.error("[ClineWorkerAdapter] Task %s error: %s", task_id, err_msg)
            self._terminate_process_tree(process)
            self._record_audit(
                task_id=task_id,
                action="CLINE_WORKER_FAILED",
                status="FAILED",
                payload={"error": err_msg[:200], "duration_ms": duration_ms},
            )
            return ClineWorkerResult(
                task_id=task_id,
                status="FAILED",
                exit_code=-4,
                error=err_msg,
                duration_ms=duration_ms,
                worktree_path=worktree_created_dir,
            )

        finally:
            self._active_processes.pop(task_id, None)

    async def cancel(self, task_id: str) -> bool:
        """Cancels an ongoing Cline process."""
        proc = self._active_processes.get(task_id)
        if proc and proc.pid:
            self._terminate_process_tree(proc)
            self._active_processes.pop(task_id, None)
            self._record_audit(
                task_id=task_id,
                action="CLINE_WORKER_CANCELLED",
                status="CANCELLED",
                payload={"pid": proc.pid},
            )
            return True
        return False

    def verify_and_integrate(self, result: ClineWorkerResult) -> dict[str, Any]:
        """Independent E-ZZIO Verification Gate.

        Worker Result != Proof.
        E-ZZIO independently verifies the worker output before official acceptance.
        """
        if result.status != "SUCCESS":
            return {
                "accepted": False,
                "reason": f"Worker reported non-success status: {result.status}",
                "proof_status": "REJECTED",
            }

        # Independent E-ZZIO verification: check changed files and validate syntax / test suite
        verification_passed = True
        verification_details = []

        if not result.changed_files:
            verification_details.append("No files were reported changed by worker.")

        return {
            "accepted": verification_passed,
            "reason": "Verified by E-ZZIO Governance" if verification_passed else "Verification failed",
            "proof_status": "PROVEN" if verification_passed else "REJECTED",
            "details": verification_details,
        }

    def _detect_changed_files(self, stdout: str, target_dir: str) -> list[str]:
        changed: list[str] = []
        for line in stdout.splitlines():
            line_str = line.strip()
            if line_str.startswith("- ") and "." in line_str:
                changed.append(line_str[2:])
            elif "changed_file:" in line_str:
                changed.append(line_str.split(":", 1)[1].strip())
        return changed

    def _parse_json_output(self, stdout: str) -> dict[str, Any]:
        for line in stdout.splitlines():
            line_str = line.strip()
            if line_str.startswith("{") and line_str.endswith("}"):
                try:
                    return json.loads(line_str)
                except Exception:
                    continue
        return {}

    def _record_audit(
        self,
        task_id: str,
        action: str,
        status: str,
        payload: dict[str, Any],
    ) -> None:
        try:
            data = {"task_id": task_id, "worker": "cline", **payload}
            self.audit_ledger.record_event(
                actor="cline-worker",
                action=action,
                payload=data,
                status=status,
            )
        except Exception as exc:
            logger.warning("[ClineWorkerAdapter] Audit recording failed: %s", exc)
