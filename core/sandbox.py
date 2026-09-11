"""core/sandbox.py - Exécuteur terminal sécurisé et barrière d'approbation."""

from __future__ import annotations

import asyncio
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Optional, Set, Tuple


COMMAND_BLACKLIST: Set[str] = {
    "rm -rf /",
    "rm -rf /*",
    ":(){ :|:& };:",
    "mkfs",
    "dd if=",
    "shutdown",
    "reboot",
}

SENSITIVE_PREFIXES: Tuple[str, ...] = (
    "rm ",
    "del ",
    "git push",
    "git reset --hard",
    "format ",
    "drop database",
)


@dataclass
class ExecutionResult:
    command: str
    exit_code: int
    stdout: str
    stderr: str
    risk_level: str  # "safe", "sensitive", "blocked"
    approved: bool = True


class SecuritySandbox:
    def __init__(self, workspace_root: Path | str = ".") -> None:
        self.workspace_root = Path(workspace_root).resolve()

    def assess_risk(self, command: str) -> Tuple[str, bool]:
        """Évalue le risque d'une commande shell.

        Retourne (niveau_de_risque, necessite_approbation).
        """
        clean = command.strip().lower()

        for blocked in COMMAND_BLACKLIST:
            if blocked in clean:
                return "blocked", False

        for sensitive in SENSITIVE_PREFIXES:
            if clean.startswith(sensitive) or f"&& {sensitive}" in clean or f"; {sensitive}" in clean:
                return "sensitive", True

        return "safe", False

    async def execute(
        self,
        command: str,
        cwd: Optional[Path | str] = None,
        timeout: float = 30.0,
        is_approved: bool = False,
    ) -> ExecutionResult:
        risk, needs_approval = self.assess_risk(command)

        if risk == "blocked":
            return ExecutionResult(
                command=command,
                exit_code=-1,
                stdout="",
                stderr="Commande bloquée : instruction interdite par la politique de sécurité E-ZzIO.",
                risk_level="blocked",
                approved=False,
            )

        if needs_approval and not is_approved:
            return ExecutionResult(
                command=command,
                exit_code=-1,
                stdout="",
                stderr="Action suspendue : approbation humaine requise avant exécution.",
                risk_level="sensitive",
                approved=False,
            )

        target_dir = Path(cwd).resolve() if cwd else self.workspace_root

        try:
            proc = await asyncio.create_subprocess_shell(
                command,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=target_dir,
            )
            stdout_b, stderr_b = await asyncio.wait_for(proc.communicate(), timeout=timeout)
            return ExecutionResult(
                command=command,
                exit_code=proc.returncode if proc.returncode is not None else 0,
                stdout=stdout_b.decode(errors="replace"),
                stderr=stderr_b.decode(errors="replace"),
                risk_level=risk,
                approved=True,
            )
        except asyncio.TimeoutError:
            try:
                proc.kill()
            except ProcessLookupError:
                pass
            return ExecutionResult(
                command=command,
                exit_code=-1,
                stdout="",
                stderr=f"Délai d'exécution dépassé ({timeout}s). Processus interrompu.",
                risk_level=risk,
                approved=True,
            )
        except Exception as exc:
            return ExecutionResult(
                command=command,
                exit_code=-1,
                stdout="",
                stderr=f"Erreur d'exécution : {exc}",
                risk_level=risk,
                approved=True,
            )
