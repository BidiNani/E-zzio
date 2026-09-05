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
    os.path.normpath("core/identity/canonical_identity.py"),
    os.path.normpath("core/security/guardrail.py"),
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

            if self._is_protected_kernel_file(abs_path):
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