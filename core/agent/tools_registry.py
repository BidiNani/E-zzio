"""E-ZZIO Coding Agent — Modular Tool Registry with Dynamic Skill Discovery."""
from __future__ import annotations
import os
import subprocess
from typing import Any, Dict, List
from core.agent.codebase_indexer import CodebaseIndexer
from core.agent.patch_engine import PatchEngine
from core.agent.agent_guard import AgentPolicyGuard
from core.agent.skill_manager import SkillManager

class ToolRegistry:
    def __init__(self, workspace_root: str):
        self.workspace_root = workspace_root
        self.indexer = CodebaseIndexer(workspace_root)
        self.patcher = PatchEngine(workspace_root)
        self.guard = AgentPolicyGuard(workspace_root)
        self.skill_manager = SkillManager(workspace_root)

    def list_tools(self) -> List[Dict[str, Any]]:
        base_tools = [
            {
                "name": "get_codebase_map",
                "description": "Fournit la cartographie structurelle compacte du dépôt.",
                "parameters": {}
            },
            {
                "name": "read_file",
                "description": "Lit le contenu d'un fichier du workspace.",
                "parameters": {"path": "chemin du fichier"}
            },
            {
                "name": "apply_patch",
                "description": "Modifie un fichier par recherche/remplacement d'un bloc exact.",
                "parameters": {"path": "chemin", "search": "texte cherché", "replace": "texte de remplacement"}
            },
            {
                "name": "run_powershell",
                "description": "Exécute une commande PowerShell (tests unitaires, diagnostic).",
                "parameters": {"command": "commande"}
            }
        ]
        
        # Injection dynamique des Skills sous forme d'outils
        for skill in self.skill_manager.discover_skills():
            base_tools.append({
                "name": skill.get("name"),
                "description": f"[SKILL] {skill.get('description')}",
                "parameters": skill.get("parameters", {})
            })

        return base_tools

    def execute(self, tool_name: str, args: Dict[str, Any]) -> str:
        # Vérification si c'est une Skill dynamique
        skills = self.skill_manager.discover_skills()
        skill_names = [s.get("name") for s in skills]

        if tool_name in skill_names:
            # Les skills passent aussi par le guard de fichier si elles manipulent des chemins
            if "path" in args:
                allowed, reason = self.guard.evaluate_intent("read_file", args)
                if not allowed:
                    return f"[RUNTIME POLICY BLOCKED] {reason}"
            return self.skill_manager.execute_skill(tool_name, args)

        # Interception souveraine par le Runtime Policy Guard pour les outils de base
        allowed, reason = self.guard.evaluate_intent(tool_name, args)
        if not allowed:
            return f"[RUNTIME POLICY BLOCKED] {reason}"

        try:
            if tool_name == "get_codebase_map":
                return self.indexer.get_compact_map()

            elif tool_name == "read_file":
                path = args.get("path", "")
                full_path = path if os.path.isabs(path) else os.path.join(self.workspace_root, path)
                with open(full_path, "r", encoding="utf-8", errors="ignore") as f:
                    return f.read()

            elif tool_name == "apply_patch":
                return self.patcher.apply_search_replace(
                    rel_path=args.get("path", ""),
                    search_block=args.get("search", ""),
                    replace_block=args.get("replace", "")
                )

            elif tool_name == "run_powershell":
                cmd = args.get("command", "")
                res = subprocess.run(
                    ["powershell.exe", "-NoProfile", "-Command", cmd],
                    cwd=self.workspace_root,
                    capture_output=True,
                    text=True,
                    timeout=60
                )
                output = res.stdout + "\n" + res.stderr
                return output.strip() or "[SUCCESS] Commande exécutée sans retour texte."

            else:
                return f"[ERROR] Outil ou Skill inconnu : {tool_name}"
        except Exception as exc:
            return f"[TOOL EXCEPTION] {exc}"
