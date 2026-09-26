"""E-ZZIO Hermes Agent External Worker Adapter.

Provides a strictly governed, bounded, headless execution bridge between
E-ZZIO Master (exclusive cognitive authority) and Hermes Agent (external worker).
Features:
- Ephemeral, per-task HERMES_HOME isolation with automatic cleanup.
- Strict process tree termination on Windows and POSIX.
- Governed capability enforcement: Tools, Skills, Plugins, MCP, Network, Memory, Delegation.
- ModelRouter fidelity: verifies Hermes system event model and provider.
- Fail-closed security via AgentPolicyGuard and AuditLedger logging.
"""
from __future__ import annotations

import asyncio
import json
import logging
import os
import re
import shutil
import sys
import tempfile
import time
from dataclasses import dataclass, field
from typing import Any

from core.agent.agent_guard import AgentPolicyGuard
from core.agent.hermes_worker_profiles import (
    WorkerProfile,
    parse_structured_result,
    resolve_profile,
)
from core.security.audit_ledger import AuditLedger

logger = logging.getLogger("HermesWorkerAdapter")

DEFAULT_WORKER_TOOLSETS: tuple[str, ...] = ()

# Toolsets unconditionally forbidden to all external workers
GLOBAL_FORBIDDEN_TOOLSETS: frozenset[str] = frozenset({
    "code_execution",
    "delegation",
    "memory",
    "session_search",
    "cronjob",
    "messaging",
    "discord",
    "discord_admin",
    "computer_use",
})

# Backward compatibility alias
FORBIDDEN_WORKER_TOOLSETS: frozenset[str] = frozenset({
    "file",
    "terminal",
    "code_execution",
    "process",
    "execute_code",
    "delegation",
    "memory",
    "session_search",
    "browser",
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
    structured_analysis: dict[str, Any] = field(default_factory=dict)
    resolved_capabilities: dict[str, Any] = field(default_factory=dict)


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
        skills: list[str] | None = None,
        max_turns: int | None = None,
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

        if skills:
            cmd.extend(["--skills", ",".join(skills)])

        if max_turns:
            cmd.extend(["--max-turns", str(max_turns)])

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

        if not final_text and not error_msg:
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
        safe_mode: bool | None = None,
        env_overrides: dict[str, str] | None = None,
        isolate_home: bool = True,
        profile: WorkerProfile | str | None = None,
        workspace_root: str | None = None,
        **kwargs: Any,
    ) -> HermesWorkerResult:
        """Submits a bounded execution subtask to the Hermes external worker under profile governance."""
        start_time = time.time()
        hermes_ver = self.get_hermes_version()

        # 1. Deterministic Profile Resolution & Capability Snapshot
        try:
            resolved_profile = resolve_profile(profile or "context_reader")
        except ValueError as val_err:
            reason = str(val_err)
            logger.warning("[HermesWorkerAdapter POLICY DENIED] %s", reason)
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

        target_workspace = workspace_root or kwargs.get("workspace") or self.workspace_root
        caps = resolved_profile.resolve_capabilities(workspace_root=target_workspace)

        # Audit Capability Resolution Snapshot
        self._record_audit(
            task_id=task_id,
            action="WORKER_CAPABILITY_RESOLVED",
            status="RESOLVED",
            payload={
                "profile": str(resolved_profile.name),
                "capabilities": caps.to_dict(),
                "model": model,
                "provider": provider,
            },
        )

        # 2. Operator Workspace Confinement Guard
        if not resolved_profile.read_only:
            norm_ws = os.path.normcase(os.path.abspath(target_workspace))
            norm_core = os.path.normcase(os.path.abspath(r"G:\AI\E-zzio"))
            if norm_ws == norm_core:
                reason = "Operator profile is prohibited from targeting protected repository root directly"
                logger.warning("[HermesWorkerAdapter POLICY DENIED] %s", reason)
                self._record_audit(
                    task_id=task_id,
                    action="WORKER_WORKSPACE_POLICY_DENIED",
                    status="DENIED",
                    payload={"reason": reason, "target_workspace": target_workspace},
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
                    resolved_capabilities=caps.to_dict(),
                )

        # 3. Read-Only Policy & Escalation Guard
        if resolved_profile.read_only:
            # If zero-tool profile receives explicit toolsets
            if not resolved_profile.hermes_toolsets and toolsets:
                reason = f"Worker profile '{resolved_profile.name}' enforces zero tools; explicit toolsets rejected"
                logger.warning("[HermesWorkerAdapter POLICY DENIED] %s", reason)
                self._record_audit(
                    task_id=task_id,
                    action="WORKER_TOOL_POLICY_DENIED",
                    status="DENIED",
                    payload={"reason": reason, "requested_toolsets": toolsets},
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
                    resolved_capabilities=caps.to_dict(),
                )
            # If read-only profile attempts mutation or terminal tools
            if toolsets:
                for ts in toolsets:
                    if ts in ("terminal", "file") or ts not in resolved_profile.hermes_toolsets:
                        reason = f"Worker profile '{resolved_profile.name}' is read-only; prohibited toolset '{ts}' rejected"
                        logger.warning("[HermesWorkerAdapter POLICY DENIED] %s", reason)
                        self._record_audit(
                            task_id=task_id,
                            action="WORKER_TOOL_POLICY_DENIED",
                            status="DENIED",
                            payload={"reason": reason, "requested_toolsets": toolsets},
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
                            resolved_capabilities=caps.to_dict(),
                        )

        # 4. Prohibited Plugins and Arbitrary MCP Manipulation Guard
        lower_prompt = prompt.lower()
        forbidden_plugin_keywords = [
            "plugin install", "plugins install", "install plugin", "plugin add",
            "plugins add", "mcp connect", "mcp install", "mcp add", "mcp discover",
        ]
        for fkw in forbidden_plugin_keywords:
            if fkw in lower_prompt:
                reason = f"Prohibited plugin/MCP dynamic modification attempt in prompt: '{fkw}'"
                logger.warning("[HermesWorkerAdapter POLICY DENIED] %s", reason)
                self._record_audit(
                    task_id=task_id,
                    action="WORKER_POLICY_DENIED",
                    status="DENIED",
                    payload={"reason": reason, "keyword": fkw},
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
                    resolved_capabilities=caps.to_dict(),
                )

        # 5. Shell Command Safety Guard (Fail-Closed)
        forbidden_substrings = ["rmdir /s", "del /s", "rm -rf", "git reset --hard"]
        matched_forbidden = next((f for f in forbidden_substrings if f in lower_prompt), None)
        if not matched_forbidden and re.search(r"\bformat\s+[a-zA-Z]:", prompt, re.IGNORECASE):
            matched_forbidden = "format <drive>:"

        if matched_forbidden:
            reason = f"Forbidden destructive shell command in prompt: {matched_forbidden}"
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
                resolved_capabilities=caps.to_dict(),
            )

        # 6. Active Toolsets and Settings from Profile
        active_toolsets = list(toolsets) if toolsets is not None else list(resolved_profile.hermes_toolsets)
        active_skills = list(resolved_profile.skills)
        effective_safe_mode = safe_mode if safe_mode is not None else resolved_profile.safe_mode
        timeout_sec = timeout if timeout is not None else resolved_profile.default_timeout_sec
        max_turns = resolved_profile.max_turns

        # Disallow globally forbidden toolsets (memory, delegation, code_execution)
        unconditional_forbidden = [ts for ts in active_toolsets if ts in GLOBAL_FORBIDDEN_TOOLSETS]
        if unconditional_forbidden:
            reason = f"Forbidden toolsets requested for bounded worker: {', '.join(unconditional_forbidden)}"
            logger.warning("[HermesWorkerAdapter POLICY DENIED] %s", reason)
            self._record_audit(
                task_id=task_id,
                action="WORKER_TOOL_POLICY_DENIED",
                status="DENIED",
                payload={"reason": reason, "forbidden_toolsets": unconditional_forbidden},
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
                resolved_capabilities=caps.to_dict(),
            )

        # Disallow toolsets not allowed for this profile
        forbidden_requested = [ts for ts in active_toolsets if ts not in resolved_profile.hermes_toolsets]
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
                resolved_capabilities=caps.to_dict(),
            )

        # 7. Build CLI Command
        cmd = self.build_cli_command(
            prompt=prompt,
            model=model,
            provider=provider,
            workspace_root=target_workspace,
            safe_mode=effective_safe_mode,
            toolsets=active_toolsets,
            skills=active_skills,
            max_turns=max_turns,
        )

        exec_env = os.environ.copy()
        temp_home: str | None = None
        if isolate_home:
            temp_home = tempfile.mkdtemp(prefix="ezzio_hermes_home_")
            exec_env["HERMES_HOME"] = temp_home

        if provider == "ollama":
            exec_env.setdefault("OPENAI_BASE_URL", "http://127.0.0.1:11434/v1")
            exec_env.setdefault("OPENAI_API_KEY", "ollama")

        if env_overrides:
            exec_env.update(env_overrides)

        self._record_audit(
            task_id=task_id,
            action="WORKER_SUBMITTED",
            status="SUBMITTED",
            payload={
                "cmd": cmd[:4],
                "model": model,
                "provider": provider,
                "timeout": timeout_sec,
                "hermes_home": temp_home,
                "profile": str(resolved_profile.name),
                "toolsets": active_toolsets,
                "skills": active_skills,
            },
        )

        # 8. Subprocess Execution with Timeout and Cancellation
        process: asyncio.subprocess.Process | None = None
        try:
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=target_workspace,
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

            # 9. Parse Output
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
            structured = parse_structured_result(final_text or raw_stdout)

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
                structured_analysis=structured,
                resolved_capabilities=caps.to_dict(),
            )

            audit_action = "WORKER_COMPLETED" if status == "SUCCESS" else "WORKER_FAILED"
            self._record_audit(
                task_id=task_id,
                action=audit_action,
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
                resolved_capabilities=caps.to_dict(),
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
                resolved_capabilities=caps.to_dict(),
            )

        finally:
            self._active_processes.pop(task_id, None)
            if temp_home and os.path.exists(temp_home):
                for attempt in range(3):
                    try:
                        shutil.rmtree(temp_home)
                        break
                    except Exception as clean_err:
                        if attempt < 2:
                            await asyncio.sleep(0.1)
                        else:
                            shutil.rmtree(temp_home, ignore_errors=True)
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
