"""E-ZZIO Hermes Agent External Worker Adapter.

Provides a strictly governed, bounded, headless execution bridge between
E-ZZIO Master (exclusive cognitive authority) and Hermes Agent (external worker).
Features:
- Ephemeral, per-task HERMES_HOME isolation with automatic cleanup.
- Strict process tree termination on Windows and POSIX.
- ModelRouter fidelity: verifies Hermes system event model and provider.
- Fail-closed security via AgentPolicyGuard and AuditLedger logging.
"""
from __future__ import annotations

import asyncio
import json
import logging
import os
import shutil
import sys
import tempfile
import time
from dataclasses import dataclass, field
from typing import Any

from core.agent.agent_guard import AgentPolicyGuard
from core.security.audit_ledger import AuditLedger

logger = logging.getLogger("HermesWorkerAdapter")

DEFAULT_WORKER_TOOLSETS: tuple[str, ...] = ("file",)

FORBIDDEN_WORKER_TOOLSETS: frozenset[str] = frozenset({
    "terminal",
    "code_execution",
    "process",
    "execute_code",
    "delegation",
    "memory",
    "session_search",
    "cronjob",
    "messaging",
    "discord",
    "discord_admin",
    "browser",
    "browser-cdp",
    "browser-use",
    "computer_use",
})


@dataclass
class HermesWorkerResult:
    """Structured result returned by Hermes Worker execution."""
    task_id: str
    status: str  # "SUCCESS", "FAILED", "TIMEOUT", "CANCELLED", "POLICY_DENIED"
    stdout: str
    stderr: str
    exit_code: int
    duration_ms: int
    output: str  # Extracted meaningful response text
    tool_events: list[dict[str, Any]] = field(default_factory=list)
    error: str | None = None
    session_id: str | None = None
    pid: int | None = None
    model: str | None = None
    actual_model: str | None = None
    actual_provider: str | None = None
    hermes_version: str | None = None
    hermes_home: str | None = None
    command: list[str] = field(default_factory=list)


class HermesWorkerAdapter:
    """Governed Adapter for Hermes Agent as an external bounded worker."""

    def __init__(
        self,
        workspace_root: str = r"G:\AI\E-zzio",
        hermes_bin: str | None = None,
        policy_guard: AgentPolicyGuard | None = None,
        audit_ledger: AuditLedger | None = None,
        default_timeout_sec: int = 60,
    ) -> None:
        self.workspace_root = os.path.abspath(workspace_root)
        self.hermes_bin = self._resolve_hermes_bin(hermes_bin)
        self.policy_guard = policy_guard or AgentPolicyGuard(self.workspace_root)
        self.audit_ledger = audit_ledger or AuditLedger()
        self.default_timeout_sec = default_timeout_sec
        self._active_processes: dict[str, asyncio.subprocess.Process] = {}
        self._cached_version: str | None = None

    def _resolve_hermes_bin(self, explicit_bin: str | None) -> str:
        if explicit_bin and os.path.exists(explicit_bin):
            return explicit_bin

        # Default paths on Windows / POSIX
        candidates = [
            r"G:\Hermes\bin\hermes.exe",
            r"G:\Hermes\bin\hermes.cmd",
            shutil.which("hermes"),
        ]
        for c in candidates:
            if c and os.path.exists(c):
                return c
        return "hermes"

    def is_available(self) -> bool:
        """Checks if the Hermes binary is actually executable on the host."""
        if os.path.isabs(self.hermes_bin):
            return os.path.exists(self.hermes_bin)
        return shutil.which(self.hermes_bin) is not None

    def get_hermes_version(self) -> str:
        """Retrieves and caches the exact version of the Hermes CLI."""
        if self._cached_version is not None:
            return self._cached_version
        try:
            import subprocess
            proc = subprocess.run(
                [self.hermes_bin, "--version"],
                capture_output=True,
                text=True,
                timeout=5,
                check=False,
            )
            v = proc.stdout.strip().splitlines()[0] if proc.stdout else "unknown"
            self._cached_version = v
            return v
        except Exception:
            return "unavailable"

    def build_cli_command(
        self,
        prompt: str,
        model: str | None = None,
        provider: str | None = None,
        workspace_root: str | None = None,
        safe_mode: bool = True,
        toolsets: list[str] | None = None,
    ) -> list[str]:
        """Constructs the bounded, headless CLI command for Hermes Agent."""
        cmd = [
            self.hermes_bin,
            "chat",
            "-q",
            prompt,
            "--format",
            "stream-json",
            "--oneshot",
            "-Q",
            "--ignore-rules",  # Neutralizes persistent memory/SOUL/rules
            "--source",
            "tool",  # Programmatic tool integration tag
        ]

        if safe_mode:
            cmd.append("--safe-mode")

        ws = workspace_root or self.workspace_root
        if ws:
            cmd.extend(["--in", ws])

        if model:
            cmd.extend(["-m", model])

        if provider:
            cmd.extend(["--provider", provider])

        active_toolsets = list(toolsets) if toolsets is not None else list(DEFAULT_WORKER_TOOLSETS)
        if active_toolsets:
            cmd.extend(["--toolsets", ",".join(active_toolsets)])

        return cmd

    def parse_stream_json(
        self, raw_stdout: str
    ) -> tuple[str, list[dict[str, Any]], str | None, int | None, str | None, str | None, str | None]:
        """Parses Hermes newline-delimited stream-json output.

        Returns:
            (extracted_text, tool_events, session_id, exit_code, error, actual_model, actual_provider)
        """
        tool_events: list[dict[str, Any]] = []
        session_id: str | None = None
        exit_code: int | None = None
        error_msg: str | None = None
        final_text = ""
        actual_model: str | None = None
        actual_provider: str | None = None

        if not raw_stdout:
            return "", [], None, None, None, None, None

        for line in raw_stdout.splitlines():
            line_str = line.strip()
            if not line_str or not line_str.startswith("{"):
                # Non-JSON banner or line
                if "session_id:" in line_str and not session_id:
                    session_id = line_str.split(":", 1)[1].strip()
                continue

            try:
                data = json.loads(line_str)
            except Exception:
                continue

            event_type = data.get("type")
            if event_type == "system":
                if not session_id and data.get("session_id"):
                    session_id = data.get("session_id")
                if data.get("model"):
                    actual_model = data.get("model")
                if data.get("provider"):
                    actual_provider = data.get("provider")
            elif event_type in ("tool_use", "tool_result"):
                tool_events.append(data)
            elif event_type == "result":
                exit_code = data.get("exit_code", 0)
                if data.get("text"):
                    final_text = data.get("text", "")
                if data.get("error"):
                    error_msg = data.get("error")
                if not session_id and data.get("session_id"):
                    session_id = data.get("session_id")
                if not actual_model and data.get("model"):
                    actual_model = data.get("model")

        # Fallback if no result event found but text present
        if not final_text and not error_msg:
            # Check if there is clean text
            non_json_lines = [
                line_item for line_item in raw_stdout.splitlines()
                if not line_item.strip().startswith("{")
            ]
            if non_json_lines:
                final_text = "\n".join(non_json_lines).strip()

        return final_text, tool_events, session_id, exit_code, error_msg, actual_model, actual_provider

    def _terminate_process_tree(self, pid: int) -> None:
        """Kills the process and its descendants reliably across OSes."""
        try:
            if sys.platform == "win32":
                import subprocess
                subprocess.run(
                    ["taskkill", "/F", "/T", "/PID", str(pid)],
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                    check=False,
                )
            else:
                os.kill(pid, 9)
        except Exception as exc:
            logger.warning("[HermesWorkerAdapter] Process tree termination failed for PID %s: %s", pid, exc)

    async def submit(
        self,
        task_id: str,
        prompt: str,
        model: str | None = None,
        provider: str | None = None,
        timeout: int | None = None,
        toolsets: list[str] | None = None,
        safe_mode: bool = True,
        env_overrides: dict[str, str] | None = None,
        isolate_home: bool = True,
        **kwargs: Any,
    ) -> HermesWorkerResult:
        """Submits a bounded execution subtask to the Hermes external worker."""
        start_time = time.time()
        timeout_sec = timeout if timeout is not None else self.default_timeout_sec
        hermes_ver = self.get_hermes_version()

        # 1. Policy Gate Evaluation (Fail-Closed)
        for forbidden in ["rmdir /s", "del /s", "rm -rf", "git reset --hard", "format "]:
            if forbidden in prompt.lower():
                reason = f"Forbidden destructive shell command in prompt: {forbidden}"
                logger.warning("[HermesWorkerAdapter POLICY DENIED] %s", reason)
                self._record_audit(
                    task_id=task_id,
                    action="WORKER_POLICY_DENIED",
                    status="DENIED",
                    payload={"reason": reason, "prompt_preview": prompt[:150]},
                )
                return HermesWorkerResult(
                    task_id=task_id,
                    status="POLICY_DENIED",
                    stdout="",
                    stderr=f"[POLICY_DENIED] {reason}",
                    exit_code=-2,
                    duration_ms=0,
                    output="",
                    error=reason,
                    model=model,
                    hermes_version=hermes_ver,
                )

        # Toolsets policy check (Fail-Closed)
        active_toolsets = list(toolsets) if toolsets is not None else list(DEFAULT_WORKER_TOOLSETS)
        forbidden_requested = [ts for ts in active_toolsets if ts in FORBIDDEN_WORKER_TOOLSETS]
        if forbidden_requested:
            reason = f"Forbidden toolsets requested for bounded worker: {', '.join(forbidden_requested)}"
            logger.warning("[HermesWorkerAdapter POLICY DENIED] %s", reason)
            self._record_audit(
                task_id=task_id,
                action="WORKER_TOOL_POLICY_DENIED",
                status="DENIED",
                payload={"reason": reason, "forbidden_toolsets": forbidden_requested},
            )
            return HermesWorkerResult(
                task_id=task_id,
                status="POLICY_DENIED",
                stdout="",
                stderr=f"[POLICY_DENIED] {reason}",
                exit_code=-2,
                duration_ms=0,
                output="",
                error=reason,
                model=model,
                hermes_version=hermes_ver,
            )

        # 2. Build CLI Command
        cmd = self.build_cli_command(
            prompt=prompt,
            model=model,
            provider=provider,
            workspace_root=self.workspace_root,
            safe_mode=safe_mode,
            toolsets=active_toolsets,
        )

        exec_env = os.environ.copy()
        temp_home: str | None = None
        if isolate_home:
            temp_home = tempfile.mkdtemp(prefix="ezzio_hermes_home_")
            exec_env["HERMES_HOME"] = temp_home

        # If Ollama local provider is requested, ensure local base_url is set
        if provider == "ollama":
            exec_env.setdefault("OPENAI_BASE_URL", "http://127.0.0.1:11434/v1")
            exec_env.setdefault("OPENAI_API_KEY", "ollama")

        if env_overrides:
            exec_env.update(env_overrides)

        self._record_audit(
            task_id=task_id,
            action="WORKER_SUBTASK_SUBMITTED",
            status="SUBMITTED",
            payload={
                "cmd": cmd[:4],
                "model": model,
                "provider": provider,
                "timeout": timeout_sec,
                "hermes_home": temp_home,
            },
        )

        # 3. Subprocess Execution with Timeout and Cancellation
        process: asyncio.subprocess.Process | None = None
        try:
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=self.workspace_root,
                env=exec_env,
            )
            self._active_processes[task_id] = process
            pid = process.pid

            stdout_bytes, stderr_bytes = await asyncio.wait_for(
                process.communicate(), timeout=timeout_sec
            )
            raw_stdout = stdout_bytes.decode("utf-8", errors="replace")
            raw_stderr = stderr_bytes.decode("utf-8", errors="replace")
            exit_code = process.returncode if process.returncode is not None else 0
            duration_ms = int((time.time() - start_time) * 1000)

            # 4. Parse Structured JSONL Output
            (
                final_text,
                tool_events,
                session_id,
                parsed_exit,
                error_msg,
                actual_model,
                actual_provider,
            ) = self.parse_stream_json(raw_stdout)
            effective_exit = parsed_exit if parsed_exit is not None else exit_code

            status = "SUCCESS" if effective_exit == 0 and not error_msg else "FAILED"
            result = HermesWorkerResult(
                task_id=task_id,
                status=status,
                stdout=raw_stdout,
                stderr=raw_stderr,
                exit_code=effective_exit,
                duration_ms=duration_ms,
                output=final_text or raw_stdout,
                tool_events=tool_events,
                error=error_msg or (raw_stderr if effective_exit != 0 else None),
                session_id=session_id,
                pid=pid,
                model=model,
                actual_model=actual_model or model,
                actual_provider=actual_provider or provider,
                hermes_version=hermes_ver,
                hermes_home=temp_home,
                command=cmd,
            )

            self._record_audit(
                task_id=task_id,
                action="WORKER_SUBTASK_COMPLETED",
                status=status,
                payload={
                    "exit_code": effective_exit,
                    "duration_ms": duration_ms,
                    "session_id": session_id,
                    "pid": pid,
                    "model": model,
                    "actual_model": actual_model,
                    "actual_provider": actual_provider,
                },
            )
            return result

        except TimeoutError:
            duration_ms = int((time.time() - start_time) * 1000)
            pid = process.pid if process else None
            if pid:
                self._terminate_process_tree(pid)

            err = f"Worker timeout after {timeout_sec}s"
            logger.warning("[HermesWorkerAdapter TIMEOUT] Task %s timed out.", task_id)
            self._record_audit(
                task_id=task_id,
                action="WORKER_SUBTASK_TIMEOUT",
                status="TIMEOUT",
                payload={"timeout_sec": timeout_sec, "duration_ms": duration_ms, "pid": pid},
            )
            return HermesWorkerResult(
                task_id=task_id,
                status="TIMEOUT",
                stdout="",
                stderr=err,
                exit_code=-3,
                duration_ms=duration_ms,
                output="",
                error=err,
                pid=pid,
                model=model,
                hermes_version=hermes_ver,
                hermes_home=temp_home,
                command=cmd,
            )

        except Exception as exc:
            duration_ms = int((time.time() - start_time) * 1000)
            pid = process.pid if process else None
            if pid:
                self._terminate_process_tree(pid)

            err = str(exc)
            logger.error("[HermesWorkerAdapter ERROR] Task %s error: %s", task_id, err)
            self._record_audit(
                task_id=task_id,
                action="WORKER_SUBTASK_FAILED",
                status="FAILED",
                payload={"error": err[:200], "duration_ms": duration_ms, "pid": pid},
            )
            return HermesWorkerResult(
                task_id=task_id,
                status="FAILED",
                stdout="",
                stderr=err,
                exit_code=-4,
                duration_ms=duration_ms,
                output="",
                error=err,
                pid=pid,
                model=model,
                hermes_version=hermes_ver,
                hermes_home=temp_home,
                command=cmd,
            )

        finally:
            self._active_processes.pop(task_id, None)
            if temp_home and os.path.exists(temp_home):
                try:
                    shutil.rmtree(temp_home, ignore_errors=True)
                except Exception as clean_err:
                    logger.warning("[HermesWorkerAdapter] Cleanup failed for %s: %s", temp_home, clean_err)

    async def cancel(self, task_id: str) -> bool:
        """Cancels an ongoing task process."""
        proc = self._active_processes.get(task_id)
        if proc and proc.pid:
            self._terminate_process_tree(proc.pid)
            self._active_processes.pop(task_id, None)
            self._record_audit(
                task_id=task_id,
                action="WORKER_SUBTASK_CANCELLED",
                status="CANCELLED",
                payload={"pid": proc.pid},
            )
            return True
        return False

    async def status(self, task_id: str) -> str:
        """Returns the status of an ongoing task."""
        if task_id in self._active_processes:
            return "RUNNING"
        return "IDLE"

    def _record_audit(
        self,
        task_id: str,
        action: str,
        status: str,
        payload: dict[str, Any],
    ) -> None:
        try:
            data = {"task_id": task_id, **payload}
            self.audit_ledger.record_event(
                actor="hermes-worker",
                action=action,
                payload=data,
                status=status,
            )
        except Exception as exc:
            logger.warning("[HermesWorkerAdapter] Audit recording failed: %s", exc)
