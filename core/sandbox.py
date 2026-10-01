"""core/sandbox.py - Exécuteur terminal sécurisé et barrière d'approbation.

Garde-fou dépôt Git (fail-closed) : une exécution est refusée si son répertoire
cwd permet à git de découvrir un dépôt réel en remontant l'arborescence
(dépôt hôte E-ZZIO inclus). Seule exception : un sandbox explicitement dédié
(``allow_git_repo=True``) dont le workspace EST lui-même un dépôt isolé
(mini-dépôt de test). Motivation : voir tests/test_sandbox.py (reverts PROVEN
du 01/10/2026 — ``git reset --hard`` exécuté par un test avec cwd sous le
basetemp intra-dépôt).
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass
from pathlib import Path

COMMAND_BLACKLIST: set[str] = {
    "rm -rf /",
    "rm -rf /*",
    ":(){ :|:& };:",
    "mkfs",
    "dd if=",
    "shutdown",
    "reboot",
}

SENSITIVE_PREFIXES: tuple[str, ...] = (
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
    def __init__(
        self,
        workspace_root: Path | str = ".",
        allow_git_repo: bool = False,
    ) -> None:
        self.workspace_root = Path(workspace_root).resolve()
        # Autorise uniquement un dépôt git ISOLÉ dont la racine est exactement
        # le workspace du sandbox (mini-dépôt de test dédié). Jamais le dépôt
        # hôte d'un projet réel.
        self.allow_git_repo = allow_git_repo

    def assess_risk(self, command: str) -> tuple[str, bool]:
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

    @staticmethod
    def _discover_git_repo_root(start: Path) -> Path | None:
        """Remonte depuis ``start`` comme le fait la découverte de git : le
        premier répertoire (start inclus) contenant un marqueur ``.git``
        (répertoire de dépôt ou fichier worktree) est la racine trouvée.
        Retourne None si aucun dépôt n'est découvert avant la racine.
        """
        current = start.resolve()
        while True:
            if (current / ".git").exists():
                return current
            parent = current.parent
            if parent == current:
                return None
            current = parent

    def _git_repo_execution_denied(self, target_dir: Path) -> bool:
        """Fail-closed : True si l'exécution dans ``target_dir`` permettrait à
        git de découvrir un dépôt réel non autorisé.

        - Aucun dépôt découvert depuis target_dir → autorisé.
        - Dépôt découvert == workspace du sandbox ET ``allow_git_repo=True``
          → autorisé (sandbox dédié, mini-dépôt de test isolé).
        - Tout autre dépôt découvert (dépôt hôte E-ZZIO, dépôt parent, ...)
          → refusé, même avec approbation explicite.
        """
        try:
            repo_root = self._discover_git_repo_root(target_dir)
        except OSError:
            return True  # fail-closed : impossible de prouver l'absence de dépôt

        if repo_root is None:
            return False
        return not (self.allow_git_repo and repo_root == self.workspace_root)

    async def execute(
        self,
        command: str,
        cwd: Path | str | None = None,
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

        target_dir = Path(cwd).resolve() if cwd else self.workspace_root

        if needs_approval and not is_approved:
            return ExecutionResult(
                command=command,
                exit_code=-1,
                stdout="",
                stderr="Action suspendue : approbation humaine requise avant exécution.",
                risk_level="sensitive",
                approved=False,
            )

        # Garde-fou dépôt Git : précède toute exécution. Une commande non
        # approuvée n'est de toute façon jamais exécutée ; une commande
        # approuvée reste bloquée si son cwd permet de découvrir un dépôt
        # réel non autorisé (l'approbation humaine ne lève pas cette barrière).
        if self._git_repo_execution_denied(target_dir):
            return ExecutionResult(
                command=command,
                exit_code=-1,
                stdout="",
                stderr=(
                    "Exécution refusée : le répertoire d'exécution permet à git de "
                    "découvrir un dépôt réel (protection du dépôt hôte E-ZZIO). "
                    "Utilisez un sandbox isolé dédié."
                ),
                risk_level="blocked",
                approved=False,
            )

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
        except TimeoutError:
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
