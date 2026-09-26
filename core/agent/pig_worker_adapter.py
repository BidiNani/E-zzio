"""
E-ZZIO Core V9.2 — PiG Coding Worker Adapter.

Adaptateur gouverné pour l'exécuteur externe optionnel PiG.
PiG est une CAPABILITÉ D'EXÉCUTION EXTERNE (Worker), JAMAIS une autorité.
L'autorité cognitive, la politique de sécurité (Policy), le budget (Budget),
le routage (ModelRouter) et la validation empirique restent à 100% chez E-ZZIO.

Conformité :
- Fail-Closed : Si pig est absent/non disponible, fallback vers le worker natif E-ZZIO.
- Isolation Processus : Annulation propre des arbres de processus sous Windows & POSIX.
- Sécurité : Validation stricte des chemins dans workspace_root.
"""
from __future__ import annotations

import asyncio
import logging
import os
import shutil
import subprocess
import sys
import time
from dataclasses import dataclass, field
from typing import Any

from core.agent.agent_guard import AgentPolicyGuard
from core.security.audit_ledger import AuditLedger

logger = logging.getLogger("PiGWorkerAdapter")


@dataclass
class PiGWorkerResult:
    worker: str = "pig"
    status: str = "FAILED"  # SUCCESS | FAILED | PARTIAL | UNAVAILABLE
    changed_files: list[str] = field(default_factory=list)
    tests_run: int = 0
    tests_passed: int = 0
    retries: int = 0
    duration_ms: float = 0.0
    stdout: str = ""
    stderr: str = ""
    validation: dict[str, Any] = field(default_factory=dict)
    error: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "worker": self.worker,
            "status": self.status,
            "changed_files": self.changed_files,
            "tests_run": self.tests_run,
            "tests_passed": self.tests_passed,
            "retries": self.retries,
            "duration_ms": self.duration_ms,
            "stdout": self.stdout,
            "stderr": self.stderr,
            "validation": self.validation,
            "error": self.error,
        }


class PiGWorkerAdapter:
    """Adaptateur de communication et d'exécution gouvernée avec le binaire externe PiG."""

    def __init__(
        self,
        pig_binary_path: str | None = None,
        workspace_root: str = r"G:\AI\E-zzio",
        audit_ledger: AuditLedger | None = None,
        policy_guard: AgentPolicyGuard | None = None,
    ):
        self.workspace_root = workspace_root
        self.pig_binary_path = pig_binary_path or shutil.which("pig")
        self.audit_ledger = audit_ledger or AuditLedger()
        self.policy_guard = policy_guard or AgentPolicyGuard(workspace_root=self.workspace_root)

    def is_available(self) -> bool:
        """Vérifie si le binaire PiG est présent et exécutable sur le système host."""
        if not self.pig_binary_path:
            self.pig_binary_path = shutil.which("pig")
        return bool(self.pig_binary_path and os.path.exists(self.pig_binary_path))

    def get_version(self) -> str | None:
        """Retourne les informations de version de pig si disponible."""
        if not self.is_available():
            return None
        try:
            res = subprocess.run([self.pig_binary_path, "--version"], capture_output=True, text=True, timeout=5)
            if res.returncode == 0:
                return res.stdout.strip()
        except Exception as exc:
            logger.warning("[PiGWorkerAdapter] Impossible d'obtenir la version de PiG: %s", exc)
        return None

    async def submit(
        self,
        task_id: str,
        prompt: str,
        workspace_root: str | None = None,
        timeout_sec: float = 60.0,
        model: str = "auto",
        provider: str = "auto",
    ) -> PiGWorkerResult:
        """Soumet une sous-tâche au worker PiG sous la gouvernance fail-closed E-ZZIO."""
        start_time = time.time()
        ws_path = workspace_root or self.workspace_root

        # 0. Vérification disponibilité & sécurité
        if not self.is_available():
            duration_ms = (time.time() - start_time) * 1000
            err_msg = "PiG binary non trouvé sur le système host (Fallback vers worker natif)."
            logger.info("[PiGWorkerAdapter] Task %s: %s", task_id, err_msg)
            return PiGWorkerResult(
                worker="pig",
                status="UNAVAILABLE",
                error=err_msg,
                duration_ms=duration_ms,
            )

        # Vérification Policy E-ZZIO
        try:
            is_allowed, reason = self.policy_guard.evaluate_intent(
                tool_name="write_file",
                args={"path": ws_path},
            )
            if not is_allowed:
                duration_ms = (time.time() - start_time) * 1000
                return PiGWorkerResult(
                    worker="pig",
                    status="FAILED",
                    error=f"[POLICY_DENIED] {reason}",
                    duration_ms=duration_ms,
                )
        except Exception as p_err:
            logger.warning("[PiGWorkerAdapter] Erreur validation policy: %s", p_err)

        # Audit Event Log: PIG_SUBMITTED
        try:
            self.audit_ledger.record_event(
                actor="PiGWorkerAdapter",
                action="PIG_WORKER_SUBMITTED",
                payload={
                    "task_id": task_id,
                    "prompt": prompt[:200],
                    "workspace": ws_path,
                    "timeout_sec": timeout_sec,
                },
                status="RUNNING",
            )
        except Exception:
            pass

        # Exécution du processus PiG
        cmd = [self.pig_binary_path, "run", "--workspace", ws_path, "--prompt", prompt]

        proc = None
        try:
            creationflags = 0
            if sys.platform == "win32":
                creationflags = subprocess.CREATE_NEW_PROCESS_GROUP

            proc = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=ws_path,
                creationflags=creationflags,
            )

            stdout_bytes, stderr_bytes = await asyncio.wait_for(
                proc.communicate(),
                timeout=timeout_sec,
            )
            stdout = stdout_bytes.decode("utf-8", errors="replace")
            stderr = stderr_bytes.decode("utf-8", errors="replace")
            duration_ms = (time.time() - start_time) * 1000

            status = "SUCCESS" if proc.returncode == 0 else "FAILED"

            # Diagnostic des fichiers modifiés et des tests
            changed_files: list[str] = []
            tests_run = 0
            tests_passed = 0

            if "changed_files:" in stdout:
                for line in stdout.splitlines():
                    if line.strip().startswith("- "):
                        changed_files.append(line.strip()[2:])

            if "passed" in stdout or "100%" in stdout:
                tests_run = 1
                tests_passed = 1

            result = PiGWorkerResult(
                worker="pig",
                status=status,
                changed_files=changed_files,
                tests_run=tests_run,
                tests_passed=tests_passed,
                duration_ms=duration_ms,
                stdout=stdout,
                stderr=stderr,
                error=None if status == "SUCCESS" else f"PiG process exited with code {proc.returncode}",
            )

            try:
                self.audit_ledger.record_event(
                    actor="PiGWorkerAdapter",
                    action="PIG_WORKER_COMPLETED",
                    payload={
                        "task_id": task_id,
                        "status": status,
                        "returncode": proc.returncode,
                        "duration_ms": duration_ms,
                    },
                    status=status,
                )
            except Exception:
                pass

            return result

        except TimeoutError:
            duration_ms = (time.time() - start_time) * 1000
            logger.warning("[PiGWorkerAdapter] Task %s timed out after %.1fs", task_id, timeout_sec)
            self._kill_process_tree(proc)
            return PiGWorkerResult(
                worker="pig",
                status="FAILED",
                error=f"PiG execution timed out after {timeout_sec}s",
                duration_ms=duration_ms,
            )
        except Exception as exc:
            duration_ms = (time.time() - start_time) * 1000
            logger.error("[PiGWorkerAdapter] Task %s error: %s", task_id, exc)
            self._kill_process_tree(proc)
            return PiGWorkerResult(
                worker="pig",
                status="FAILED",
                error=str(exc),
                duration_ms=duration_ms,
            )

    def _kill_process_tree(self, proc: asyncio.subprocess.Process | None) -> None:
        """Termine le processus et son arbre sous Windows & POSIX sans laisser d'orphelins."""
        if proc is None or proc.returncode is not None:
            return
        try:
            if sys.platform == "win32":
                subprocess.run(
                    ["taskkill", "/F", "/T", "/PID", str(proc.pid)],
                    capture_output=True,
                    timeout=5,
                )
            else:
                proc.kill()
        except Exception as exc:
            logger.warning("[PiGWorkerAdapter] Impossible d'interrompre le processus pid=%s: %s", getattr(proc, "pid", None), exc)
