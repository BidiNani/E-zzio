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
from typing import Dict, Any, Tuple

# Fichiers/dossiers que l'agent ne doit JAMAIS pouvoir modifier lui-même,
# quelle que soit la tâche demandée. Cette liste doit rester courte et
# volontairement rigide : c'est le filet de sécurité, pas une feature.
PROTECTED_RELATIVE_PATHS = [
    os.path.join("core", "agent", "agent_guard.py"),
    os.path.join("core", "agent", "patch_engine.py"),
    os.path.join("core", "agent", "tools_registry.py"),
    os.path.join("core", "agent", "coding_agent_loop.py"),
    os.path.join("core", "agent", "agent_provider.py"),
]

FORBIDDEN_NAME_FRAGMENTS = [".git", "unified_vault.py"]


class AgentPolicyGuard:
    def __init__(self, workspace_root: str):
        self.workspace_root = os.path.abspath(workspace_root)

    def _is_within_workspace(self, abs_path: str) -> bool:
        """Vérifie via os.path.commonpath (pas startswith) que abs_path est
        réellement DANS workspace_root, sans être trompé par un dossier
        voisin qui partage le même préfixe de chaîne."""
        try:
            common = os.path.commonpath([self.workspace_root, abs_path])
        except ValueError:
            # Chemins sur des lecteurs différents (Windows) -> jamais confiné
            return False
        return common == self.workspace_root

    def _is_protected_kernel_file(self, abs_path: str) -> bool:
        for rel in PROTECTED_RELATIVE_PATHS:
            if abs_path == os.path.join(self.workspace_root, rel):
                return True
        return any(fragment in abs_path for fragment in FORBIDDEN_NAME_FRAGMENTS)

    def evaluate_intent(self, tool_name: str, args: Dict[str, Any]) -> Tuple[bool, str]:
        """Évalue si l'outil et ses arguments respectent la politique de sécurité du Runtime."""

        # 1. Protection du Filesystem / Patches
        if tool_name in ["read_file", "apply_patch", "write_file"]:
            path = args.get("path", "")
            if not path:
                return False, "Chemin de fichier manquant pour l'opération."

            abs_path = os.path.abspath(
                path if os.path.isabs(path) else os.path.join(self.workspace_root, path)
            )

            if not self._is_within_workspace(abs_path):
                return False, f"[SECURITY DENY] Tentative d'accès hors-limites interdite : {path}"

            if self._is_protected_kernel_file(abs_path):
                return False, f"[SECURITY DENY] Zone protégée du kernel inaccessible aux agents : {path}"

        # 2. Gouvernance des commandes Shell / PowerShell
        elif tool_name == "run_powershell":
            cmd = args.get("command", "").lower()
            forbidden_keywords = [
                "rm -rf",
                "format ",
                "diskpart",
                "del /s /q c:",
                "remove-item -recurse -force",
                "remove-item -force -recurse",
                "rd /s /q",
                "rmdir /s /q",
            ]
            for kw in forbidden_keywords:
                if kw in cmd:
                    return False, f"[SECURITY DENY] Commande système dangereuse interceptée : {kw}"

        return True, "ALLOW"