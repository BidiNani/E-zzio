"""E-ZZIO Core — InternalToolBridge.

Interface d'exécution d'outils pour ``coder_worker`` : lecture/écriture
de fichiers, commandes git, commandes shell contrôlées.

**Garde-fous** :
- Whitelist de commandes shell (pas de ``rm -rf /``)
- Whitelist de commandes git (pas de ``git push --force``)
- Chemins confinés dans ``workspace_root`` (pas de sortie du projet)
- Timeouts sur toutes les commandes
- ``dry_run`` pour simuler sans exécuter

**Usage** :
    bridge = InternalToolBridge(root_dir="G:/AI/E-zzio", dry_run=True)
    bridge.read_file("core/coding/protocol.py")
    bridge.write_file("tests/unit/test_foo.py", "def test(): pass")
    bridge.git_status()
    bridge.run_command("pytest", ["tests/unit/test_foo.py"])
"""
from __future__ import annotations

import logging
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


# ============================================================
# WHITELISTS
# ============================================================

ALLOWED_SHELL_COMMANDS = frozenset([
    "pytest", "ruff", "python", "python3", "python.exe",
    "pip", "pip3", "pip.exe",
    "git", "ls", "dir", "cat", "type", "echo",
])

ALLOWED_GIT_COMMANDS = frozenset([
    "status", "diff", "log", "add", "commit", "restore",
    "checkout", "branch", "stash", "ls-files", "show",
    "rev-parse", "rev-list", "config",
    "push",  # autorisé, mais pas --force
])

FORBIDDEN_GIT_FLAGS = frozenset([
    "--force", "-f", "--hard", "--delete", "-D",
])


@dataclass
class ToolResult:
    """Résultat d'une exécution d'outil."""
    success: bool
    stdout: str = ""
    stderr: str = ""
    return_code: int = 0
    dry_run: bool = False
    error: str = ""


class InternalToolBridge:
    """Bridge interne pour l'exécution d'outils.

    Remplace le bridge Antigravity décommissionné.
    """

    def __init__(
        self,
        root_dir: Path | str = ".",
        dry_run: bool = False,
        timeout_seconds: int = 60,
    ) -> None:
        self.root_dir = Path(root_dir).resolve()
        self.dry_run = dry_run
        self.timeout_seconds = timeout_seconds

        if not self.root_dir.exists():
            raise ValueError(f"root_dir inexistant : {self.root_dir}")

    # --------------------------------------------------------
    # FICHIERS
    # --------------------------------------------------------

    def _resolve_path(self, rel_path: str) -> Path:
        """Résout un chemin relatif et vérifie qu'il est dans le workspace."""
        p = (self.root_dir / rel_path).resolve()
        try:
            p.relative_to(self.root_dir)
        except ValueError as exc:
            raise ValueError(f"Chemin hors workspace : {rel_path}") from exc
        return p

    def read_file(self, rel_path: str) -> ToolResult:
        """Lit un fichier dans le workspace."""
        try:
            p = self._resolve_path(rel_path)
            if not p.exists():
                return ToolResult(success=False, error=f"Fichier absent : {rel_path}")
            content = p.read_text(encoding="utf-8")
            return ToolResult(success=True, stdout=content)
        except Exception as exc:
            return ToolResult(success=False, error=str(exc))

    def write_file(self, rel_path: str, content: str) -> ToolResult:
        """Écrit un fichier dans le workspace."""
        try:
            p = self._resolve_path(rel_path)
            if self.dry_run:
                return ToolResult(
                    success=True,
                    stdout=f"[DRY-RUN] Écrirait {len(content)} octets dans {rel_path}",
                    dry_run=True,
                )
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_text(content, encoding="utf-8")
            logger.info("Fichier écrit : %s", rel_path)
            return ToolResult(success=True, stdout=f"{rel_path} écrit")
        except Exception as exc:
            return ToolResult(success=False, error=str(exc))

    def file_exists(self, rel_path: str) -> bool:
        """Vérifie l'existence d'un fichier."""
        try:
            return self._resolve_path(rel_path).exists()
        except Exception:
            return False

    def list_files(self, rel_dir: str = ".", pattern: str = "*") -> list[str]:
        """Liste les fichiers dans un dossier."""
        try:
            p = self._resolve_path(rel_dir)
            return [str(f.relative_to(self.root_dir)) for f in p.glob(pattern)]
        except Exception:
            return []

    # --------------------------------------------------------
    # SHELL
    # --------------------------------------------------------

    def run_command(self, command: str, args: list[str] | None = None) -> ToolResult:
        """Exécute une commande whitelistée."""
        args = args or []
        cmd_name = Path(command).stem.lower()

        if cmd_name not in ALLOWED_SHELL_COMMANDS:
            return ToolResult(success=False, error=f"Commande non autorisée : {command}")

        cmd = [command, *args]
        if self.dry_run:
            return ToolResult(
                success=True,
                stdout=f"[DRY-RUN] Exécuterait : {' '.join(cmd)}",
                dry_run=True,
            )

        try:
            result = subprocess.run(
                cmd,
                cwd=self.root_dir,
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                timeout=self.timeout_seconds,
                check=False,
            )
            return ToolResult(
                success=result.returncode == 0,
                stdout=result.stdout,
                stderr=result.stderr,
                return_code=result.returncode,
            )
        except subprocess.TimeoutExpired:
            return ToolResult(success=False, error=f"Timeout après {self.timeout_seconds}s")
        except Exception as exc:
            return ToolResult(success=False, error=str(exc))

    # --------------------------------------------------------
    # GIT
    # --------------------------------------------------------

    def git_command(self, *args: str) -> ToolResult:
        """Exécute une commande git whitelistée."""
        if not args:
            return ToolResult(success=False, error="Aucun argument git")

        subcommand = args[0].lower()
        if subcommand not in ALLOWED_GIT_COMMANDS:
            return ToolResult(success=False, error=f"Commande git non autorisée : git {subcommand}")

        # Vérifier les flags interdits
        for arg in args:
            if arg in FORBIDDEN_GIT_FLAGS:
                return ToolResult(success=False, error=f"Flag git interdit : {arg}")

        return self.run_command("git", list(args))

    def git_status(self) -> ToolResult:
        return self.git_command("status", "--short")

    def git_diff(self) -> ToolResult:
        return self.git_command("diff")

    def git_add(self, *paths: str) -> ToolResult:
        return self.git_command("add", *paths)

    def git_commit(self, message: str) -> ToolResult:
        return self.git_command("commit", "-m", message)

    def git_log(self, limit: int = 5) -> ToolResult:
        return self.git_command("log", "--oneline", f"-{limit}")

    def git_restore(self, path: str) -> ToolResult:
        return self.git_command("restore", path)

    # --------------------------------------------------------
    # TESTS
    # --------------------------------------------------------

    def run_pytest(self, test_path: str | None = None, extra_args: list[str] | None = None) -> ToolResult:
        """Exécute pytest sur un fichier ou tout le dossier tests."""
        args = ["-m", "pytest"]
        if test_path:
            args.append(test_path)
        else:
            args.append("tests/")
        args.append("-q")
        if extra_args:
            args.extend(extra_args)
        return self.run_command("python", args)

    def run_ruff(self, path: str = ".") -> ToolResult:
        """Exécute ruff check sur un chemin."""
        return self.run_command("ruff", ["check", path])

    # --------------------------------------------------------
    # FICHIER DE STATUT
    # --------------------------------------------------------

    def get_context(self) -> dict[str, Any]:
        """Retourne un contexte minimal sur l'état du workspace."""
        return {
            "root_dir": str(self.root_dir),
            "dry_run": self.dry_run,
            "git_status": self.git_status().stdout if not self.dry_run else "[DRY-RUN]",
            "git_log": self.git_log(3).stdout if not self.dry_run else "[DRY-RUN]",
        }


__all__ = [
    "InternalToolBridge",
    "ToolResult",
    "ALLOWED_SHELL_COMMANDS",
    "ALLOWED_GIT_COMMANDS",
]
