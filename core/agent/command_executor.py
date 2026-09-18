"""E-ZZIO Coding Agent — Governed Command Executor with Safety Gate & Audit.

Fournit une exécution strictement gouvernée des commandes système :
- Allowlist de binaires et sous-commandes autorisés (python, pytest, ruff, git inspect)
- Denylist absolue des commandes destructrices et d'évasion (git reset --hard, clean, rm, format, shutdown)
- Masquage cryptographique / regex des secrets dans les logs d'audit
- Traçabilité JSONL dans state/audit/governed_commands.jsonl
- Contrôle de budget et de timeout avec terminaison propre
"""
from __future__ import annotations

import json
import os
import re
import shlex
import subprocess
import time
from typing import Any

SAFE_EXECUTABLES = {
    "python",
    "python.exe",
    "pytest",
    "pytest.exe",
    "ruff",
    "ruff.exe",
    "git",
    "git.exe",
}

FORBIDDEN_SHELL_OPERATORS = [
    r"&&",
    r"\|\|",
    r">>",
    r">",
    r"\|",
    r";",
    r"`",
    r"\$\(",
]

SAFE_GIT_SUBCOMMANDS = {
    "status",
    "diff",
    "show",
    "log",
    "branch",
    "rev-parse",
    "describe",
    "tag",
}

FORBIDDEN_COMMAND_PATTERNS = [
    r"git\s+reset\s+--hard",
    r"git\s+clean\s+-[a-zA-Z]*f",
    r"git\s+checkout\s+-[a-zA-Z]*f",
    r"git\s+rebase",
    r"git\s+push\s+--force",
    r"git\s+filter-branch",
    r"git\s+filter-repo",
    r"git\s+gc",
    r"git\s+prune",
    r"remove-item\b.*-recurse.*-force",
    r"remove-item\b.*-force.*-recurse",
    r"del\s+.*\/s",
    r"rmdir\s+.*\/s",
    r"rd\s+.*\/s",
    r"rm\s+-rf",
    r"format\s+[a-zA-Z]:",
    r"shutdown\b",
    r"stop-computer\b",
    r"diskpart\b",
    r"mkfs",
    r"curl\b",
    r"wget\b",
    r"nc\b",
    r"-encodedcommand",
    r"\biex\b",
    r"invoke-expression\b",
    r"start-process\b",
]

SECRET_PATTERNS = [
    re.compile(r"AIza[0-9A-Za-z\-_]{30,}"),
    re.compile(r"gsk_[0-9A-Za-z]{30,}"),
    re.compile(r"nvapi-[0-9A-Za-z\-_]{20,}"),
    re.compile(r"Bearer\s+[A-Za-z0-9\-\._~\+\/]{20,}="),
    re.compile(r"-----BEGIN (?:RSA )?PRIVATE KEY-----[\s\S]*?-----END (?:RSA )?PRIVATE KEY-----"),
]


def redact_secrets(text: str) -> str:
    """Masque tout credential ou jeton sensible détecté."""
    if not text:
        return ""
    sanitized = text
    for pattern in SECRET_PATTERNS:
        sanitized = pattern.sub("[REDACTED_SECRET]", sanitized)
    return sanitized


class GovernedCommandExecutor:
    """Exécuteur gouverné avec classification de sécurité, budget et traçabilité."""

    def __init__(
        self,
        workspace_root: str,
        max_commands_budget: int = 50,
        default_timeout_sec: int = 60,
    ):
        self.workspace_root = os.path.abspath(workspace_root)
        self.audit_dir = os.path.join(self.workspace_root, "state", "audit")
        os.makedirs(self.audit_dir, exist_ok=True)
        self.audit_file = os.path.join(self.audit_dir, "governed_commands.jsonl")
        self.max_commands_budget = max_commands_budget
        self.default_timeout_sec = default_timeout_sec
        self.executed_commands_count = 0

    def classify_action(self, command_str: str) -> tuple[str, str]:
        """Classifie une commande en SAFE, SENSITIVE, ou CRITICAL.
        Applique une politique strictement FAIL-CLOSED : tout exécutable ou opérateur
        non explicitement autorisé est rejeté avec la classification CRITICAL.

        Returns:
            (classification, reason)
        """
        cmd_clean = command_str.strip()
        if not cmd_clean:
            return "CRITICAL", "Commande vide refusée."

        cmd_lower = cmd_clean.lower()

        # 1. Vérification des motifs interdits absolus
        for pattern in FORBIDDEN_COMMAND_PATTERNS:
            if re.search(pattern, cmd_lower):
                return "CRITICAL", f"Commande destructrice ou d'évasion interceptée: {pattern}"

        # 2. Interdiction absolue du chaînage ou de redirection par opérateurs shell
        for op in FORBIDDEN_SHELL_OPERATORS:
            if re.search(op, cmd_clean):
                return "CRITICAL", f"Opérateur shell d'évasion ou de chaînage interdit détecté: {op}"

        # 3. Extraction déterministe du premier exécutable
        cmd_to_parse = cmd_clean
        if cmd_to_parse.startswith("&"):
            cmd_to_parse = cmd_to_parse[1:].strip()

        try:
            tokens = shlex.split(cmd_to_parse, posix=False)
        except Exception as exc:
            return "CRITICAL", f"Erreur de syntaxe dans la commande: {exc}"

        if not tokens:
            return "CRITICAL", "Aucun exécutable identifié dans la commande."

        raw_exe = tokens[0].strip("\"'")
        base_exe = os.path.basename(raw_exe).lower()

        # 4. RÈGLE FAIL-CLOSED : Rejet systématique de tout exécutable non présent dans SAFE_EXECUTABLES
        if base_exe not in SAFE_EXECUTABLES:
            return "CRITICAL", f"[SECURITY POLICY DENIED] Exécutable non autorisé: '{raw_exe}'"

        # 5. Gouvernance spécifique pour Git
        if base_exe in ["git", "git.exe"]:
            if len(tokens) > 1:
                sub = tokens[1].lower().strip("\"'")
                if sub in ["commit", "add", "stash"]:
                    return "SENSITIVE", f"Opération git modificatrice d'état: {sub}"
                if sub in SAFE_GIT_SUBCOMMANDS:
                    return "SAFE", f"Opération git d'inspection sécurisée: {sub}"
                return "SENSITIVE", f"Opération git non-inspectrice: {sub}"
            return "SAFE", "Opération git d'inspection sécurisée: status"

        # 6. Outils de test et d'analyse statique
        if base_exe in ["pytest", "pytest.exe", "ruff", "ruff.exe"]:
            return "SAFE", f"Suite de tests ou diagnostic en lecture seule: {base_exe}"

        # 7. Gouvernance spécifique pour Python
        if base_exe in ["python", "python.exe"]:
            if len(tokens) > 1:
                arg1 = tokens[1].lower().strip("\"'")
                if arg1 in ["-m", "pytest"]:
                    return "SAFE", "Exécution de module de test python autorisée"
                if arg1.endswith(".py"):
                    return "SAFE", f"Exécution de script python autorisée: {tokens[1]}"
                if arg1 in ["--version", "-v", "-h", "--help"]:
                    return "SAFE", "Inspection de l'interpréteur python"
                return "SAFE", f"Exécution python gouvernée: {tokens[1]}"
            return "SAFE", "Interpréteur python interactif/gouverné"

        return "CRITICAL", f"[SECURITY POLICY DENIED] Action non autorisée pour l'exécutable: {base_exe}"

    def execute(
        self,
        command: str,
        cwd: str | None = None,
        timeout: int | None = None,
        env: dict[str, str] | None = None,
    ) -> dict[str, Any]:
        """Exécute une commande sous gouvernance stricte et enregistre l'audit."""
        start_time = time.time()
        exec_cwd = os.path.abspath(cwd) if cwd else self.workspace_root

        # Vérification du budget
        if self.executed_commands_count >= self.max_commands_budget:
            res = {
                "success": False,
                "exit_code": -1,
                "stdout": "",
                "stderr": f"[BUDGET EXCEEDED] Nombre maximum de commandes ({self.max_commands_budget}) atteint.",
                "duration_ms": 0,
                "classification": "CRITICAL",
                "status": "BUDGET_REJECTED",
            }
            self._log_audit(command, exec_cwd, res)
            return res

        # Évaluation de l'action
        classification, reason = self.classify_action(command)
        if classification == "CRITICAL":
            res = {
                "success": False,
                "exit_code": -2,
                "stdout": "",
                "stderr": f"[SECURITY POLICY DENIED] {reason}",
                "duration_ms": 0,
                "classification": "CRITICAL",
                "status": "POLICY_DENIED",
            }
            self._log_audit(command, exec_cwd, res)
            return res

        # Détermination du timeout
        timeout_sec = timeout if timeout is not None else self.default_timeout_sec

        # Exécution du process
        self.executed_commands_count += 1
        pwsh_cmd = command.strip()
        if pwsh_cmd.startswith('"') or pwsh_cmd.startswith("'"):
            pwsh_cmd = f"& {pwsh_cmd}"
        try:
            # Sur Windows, powershell.exe est le shell d'exécution gouverné
            process = subprocess.run(
                ["powershell.exe", "-NoProfile", "-NonInteractive", "-Command", pwsh_cmd],
                cwd=exec_cwd,
                capture_output=True,
                text=True,
                timeout=timeout_sec,
                env=env or os.environ.copy(),
            )
            duration_ms = int((time.time() - start_time) * 1000)
            res = {
                "success": process.returncode == 0,
                "exit_code": process.returncode,
                "stdout": process.stdout or "",
                "stderr": process.stderr or "",
                "duration_ms": duration_ms,
                "classification": classification,
                "status": "COMPLETED" if process.returncode == 0 else "FAILED",
            }
        except subprocess.TimeoutExpired as exc:
            duration_ms = int((time.time() - start_time) * 1000)
            res = {
                "success": False,
                "exit_code": -3,
                "stdout": exc.stdout or "" if hasattr(exc, "stdout") else "",
                "stderr": f"[TIMEOUT] Commande interrompue après {timeout_sec}s.",
                "duration_ms": duration_ms,
                "classification": classification,
                "status": "TIMEOUT",
            }
        except Exception as exc:
            duration_ms = int((time.time() - start_time) * 1000)
            res = {
                "success": False,
                "exit_code": -4,
                "stdout": "",
                "stderr": f"[EXECUTION ERROR] {exc}",
                "duration_ms": duration_ms,
                "classification": classification,
                "status": "ERROR",
            }

        self._log_audit(command, exec_cwd, res)
        return res

    def _log_audit(self, command: str, cwd: str, result: dict[str, Any]) -> None:
        """Écrit l'événement dans le journal d'audit JSONL avec masquage des secrets."""
        clean_cmd = redact_secrets(command)
        clean_stdout = redact_secrets(result.get("stdout", ""))[:2000]
        clean_stderr = redact_secrets(result.get("stderr", ""))[:2000]

        entry = {
            "timestamp": time.time(),
            "iso_time": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "command": clean_cmd,
            "cwd": cwd,
            "classification": result.get("classification", "UNKNOWN"),
            "status": result.get("status", "UNKNOWN"),
            "exit_code": result.get("exit_code"),
            "duration_ms": result.get("duration_ms", 0),
            "stdout_summary": clean_stdout,
            "stderr_summary": clean_stderr,
        }
        try:
            with open(self.audit_file, "a", encoding="utf-8") as f:
                f.write(json.dumps(entry) + "\n")
        except Exception:
            pass
