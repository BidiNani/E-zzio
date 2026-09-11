"""E-ZZIO Coding Agent — Runtime Permission Interceptor & Policy Guard.

Version corrigée : deux failles réelles identifiées dans la version d'origine.
1) La vérification de confinement utilisait str.startswith(), vulnérable au
   bug de préfixe (ex: G:\\AI\\E-zzio_FINAL_BACKUP commence par G:\\AI\\E-zzio).
   -> corrigé avec os.path.commonpath().
2) Le noyau agentique lui-même (agent_guard.py, patch_engine.py,
   tools_registry.py, coding_agent_loop.py, agent_provider.py) n'était pas
   protégé contre l'auto-modification. -> ajouté à la zone interdite.
"""
from __future__ import annotations
import os
import re
from typing import Dict, Any, Tuple

PROTECTED_RELATIVE_PATHS = [
    os.path.normpath("core/agent/agent_guard.py"),
    os.path.normpath("core/agent/patch_engine.py"),
    os.path.normpath("core/agent/tools_registry.py"),
    os.path.normpath("core/agent/coding_agent_loop.py"),
    os.path.normpath("core/agent/agent_provider.py"),
    os.path.normpath("core/agent/command_executor.py"),
    os.path.normpath("core/agent/evidence_logger.py"),
    os.path.normpath("core/agent/complex_task_orchestrator.py"),
    os.path.normpath("core/identity/canonical_identity.py"),
    os.path.normpath("core/security/guardrail.py"),
    os.path.normpath("docs/FROZEN_CORE_MANIFEST.json"),
    os.path.normpath("secrets/.env"),
    os.path.normpath("web_server.py"),
    os.path.normpath("pyproject.toml"),
]

FORBIDDEN_NAME_FRAGMENTS = [".git", "unified_vault.py"]

FORBIDDEN_SHELL_PATTERNS = [
    r"remove-item\b.*-recurse.*-force",
    r"remove-item\b.*-force.*-recurse",
    r"del\s+.*\/s",
    r"rmdir\s+.*\/s",
    r"rd\s+.*\/s",
    r"rm\s+-rf",
    r"git\s+reset\s+--hard",
    r"git\s+clean\s+-[a-zA-Z]*f",
    r"git\s+checkout\s+-[a-zA-Z]*f",
    r"git\s+rebase",
    r"git\s+push\s+--force",
    r"format\s+[a-zA-Z]:",
    r"shutdown\b",
    r"stop-computer\b",
    r"diskpart\b",
]


class AgentPolicyGuard:
    def __init__(self, workspace_root: str):
        self.workspace_root = os.path.normcase(os.path.abspath(workspace_root))

    def _is_within_workspace(self, abs_path: str) -> bool:
        """Vérifie via os.path.commonpath que abs_path est réellement DANS workspace_root."""
        try:
            norm_target = os.path.normcase(os.path.abspath(abs_path))
            common = os.path.commonpath([self.workspace_root, norm_target])
            return common == self.workspace_root
        except (ValueError, Exception):
            return False

    def _is_protected_kernel_file(self, abs_path: str) -> bool:
        norm_abs = os.path.normcase(os.path.abspath(abs_path))
        for rel in PROTECTED_RELATIVE_PATHS:
            expected = os.path.normcase(os.path.abspath(os.path.join(self.workspace_root, rel)))
            if norm_abs == expected:
                return True
        return any(fragment.lower() in norm_abs for fragment in FORBIDDEN_NAME_FRAGMENTS)

    def evaluate_intent(self, tool_name: str, args: Dict[str, Any]) -> Tuple[bool, str]:
        """Évalue si l'outil et ses arguments respectent la politique de sécurité du Runtime."""

        # 1. Protection du Filesystem / Patches
        if tool_name in ["read_file", "apply_patch", "write_file", "read_file_slice"]:
            path = args.get("path", "")
            if not path:
                return False, "Chemin de fichier manquant pour l'opération."

            abs_path = os.path.abspath(
                path if os.path.isabs(path) else os.path.join(self.workspace_root, path)
            )

            if not self._is_within_workspace(abs_path):
                return False, f"[SECURITY DENY] Accès hors du workspace interdit : {path}"

            if tool_name in ["apply_patch", "write_file"] and self._is_protected_kernel_file(abs_path):
                return False, f"[SECURITY DENY] Modification d'un composant critique de sécurité interdit : {path}"

        # 2. Gouvernance des commandes Shell / PowerShell
        elif tool_name in ["run_powershell", "run_test_file"]:
            cmd = args.get("command", "")
            if not cmd and tool_name == "run_test_file":
                cmd = args.get("path", "") or args.get("test_path", "")
            cmd_lower = cmd.lower()

            for pat in FORBIDDEN_SHELL_PATTERNS:
                if re.search(pat, cmd_lower):
                    return False, f"[SECURITY DENY] Commande système dangereuse interceptée : {cmd}"

        return True, "ALLOW"

    def classify_action(self, tool_name: str, args: Dict[str, Any]) -> Tuple[str, str]:
        """Classifie une intention en SAFE, SENSITIVE, ou CRITICAL."""
        # 1. Vérification sécurité préalable
        allowed, reason = self.evaluate_intent(tool_name, args)
        if not allowed:
            return "CRITICAL", reason

        # 2. Outils de lecture / inspection -> SAFE
        if tool_name in ["read_file", "read_file_slice", "grep_codebase", "find_files", "get_codebase_map"]:
            return "SAFE", "Opération de lecture ou recherche"

        # 3. Tests unitaires -> SAFE
        if tool_name == "run_test_file":
            return "SAFE", "Exécution de tests unitaires"

        # 4. Modifications de code -> SENSITIVE
        if tool_name in ["write_file", "apply_patch"]:
            return "SENSITIVE", "Modification de fichier source"

        # 5. Commandes PowerShell
        if tool_name == "run_powershell":
            cmd = args.get("command", "").lower()
            if any(t in cmd for t in ["pytest", "git status", "git diff", "git log", "git show", "ruff"]):
                return "SAFE", "Commande shell de test ou d'inspection"
            return "SENSITIVE", "Commande shell susceptible d'altérer l'état"

        return "SAFE", "Action autorisée par défaut"

    def review_patch(self, rel_path: str, proposed_code: str) -> Tuple[bool, str]:
        """Effectue une revue statique automatisée du code avant validation."""
        import ast
        if rel_path.endswith(".py"):
            try:
                ast.parse(proposed_code)
            except SyntaxError as exc:
                return False, f"[SYNTAX ERROR] Échec de parsing AST : {exc}"

        lines = proposed_code.splitlines()
        if len(lines) > 2000:
            return False, f"[SIZE LIMIT] Fichier proposé trop volumineux ({len(lines)} lignes)."

        return True, "REVIEW_PASS"


class CodingAgentBudget:
    """Suivi et restriction du budget de changement d'un cycle agentique."""

    def __init__(
        self,
        max_iterations: int = 10,
        max_files: int = 15,
        max_diff_lines: int = 1000,
        max_runtime_sec: int = 600,
        max_commands: int = 30,
    ):
        import time
        self.max_iterations = max_iterations
        self.max_files = max_files
        self.max_diff_lines = max_diff_lines
        self.max_runtime_sec = max_runtime_sec
        self.max_commands = max_commands

        self.iterations_count = 0
        self.modified_files = set()
        self.total_diff_lines = 0
        self.commands_count = 0
        self.start_time = time.time()

    def record_iteration(self) -> Tuple[bool, str]:
        self.iterations_count += 1
        if self.iterations_count > self.max_iterations:
            return False, f"[BUDGET EXCEEDED] Nombre max d'itérations ({self.max_iterations}) dépassé."
        return True, "OK"

    def record_file(self, rel_path: str) -> Tuple[bool, str]:
        self.modified_files.add(rel_path)
        if len(self.modified_files) > self.max_files:
            return False, f"[BUDGET EXCEEDED] Nombre max de fichiers modifiés ({self.max_files}) dépassé."
        return True, "OK"

    def record_diff_lines(self, lines_count: int) -> Tuple[bool, str]:
        self.total_diff_lines += lines_count
        if self.total_diff_lines > self.max_diff_lines:
            return False, f"[BUDGET EXCEEDED] Volume de diff max ({self.max_diff_lines} lignes) dépassé."
        return True, "OK"

    def record_command(self) -> Tuple[bool, str]:
        self.commands_count += 1
        if self.commands_count > self.max_commands:
            return False, f"[BUDGET EXCEEDED] Nombre max de commandes ({self.max_commands}) dépassé."
        return True, "OK"

    def check_runtime(self) -> Tuple[bool, str]:
        import time
        elapsed = time.time() - self.start_time
        if elapsed > self.max_runtime_sec:
            return False, f"[BUDGET EXCEEDED] Temps d'exécution max ({self.max_runtime_sec}s) dépassé."
        return True, "OK"