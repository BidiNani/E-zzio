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
                "name": "grep_codebase",
                "description": "Recherche une chaîne de caractères dans les fichiers du workspace.",
                "parameters": {"query": "terme à chercher"}
            },
            {
                "name": "find_files",
                "description": "Recherche des fichiers par motif de nom dans le workspace.",
                "parameters": {"pattern": "motif de recherche"}
            },
            {
                "name": "read_file",
                "description": "Lit le contenu d'un fichier du workspace.",
                "parameters": {"path": "chemin du fichier"}
            },
            {
                "name": "read_file_slice",
                "description": "Lit une plage spécifique de lignes d'un fichier.",
                "parameters": {"path": "chemin", "start_line": "début", "end_line": "fin"}
            },
            {
                "name": "write_file",
                "description": "Crée ou réécrit un fichier dans le workspace.",
                "parameters": {"path": "chemin du fichier", "content": "contenu"}
            },
            {
                "name": "apply_patch",
                "description": "Modifie un fichier par recherche/remplacement d'un bloc exact.",
                "parameters": {"path": "chemin", "search": "texte cherché", "replace": "texte de remplacement"}
            },
            {
                "name": "run_test_file",
                "description": "Exécute un fichier de test pytest ciblé.",
                "parameters": {"test_path": "chemin du fichier de test"}
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

    def execute_tool(self, tool_name: str, args: Dict[str, Any]) -> str:
        """Alias canonique d'exécution d'outil."""
        return self.execute(tool_name, args)

    def execute(self, tool_name: str, args: Dict[str, Any]) -> str:
        # Vérification si c'est une Skill dynamique
        skills = self.skill_manager.discover_skills()
        skill_names = [s.get("name") for s in skills]

        if tool_name in skill_names:
            if "path" in args:
                allowed, reason = self.guard.evaluate_intent("read_file", args)
                if not allowed:
                    return f"[RUNTIME POLICY BLOCKED] {reason}"
            return self.skill_manager.execute_skill(tool_name, args)

        allowed, reason = self.guard.evaluate_intent(tool_name, args)
        if not allowed:
            return f"[RUNTIME POLICY BLOCKED] {reason}"

        try:
            if tool_name == "get_codebase_map":
                return self.indexer.get_compact_map()

            elif tool_name == "grep_codebase":
                query = args.get("query", "").lower()
                matches = []
                for root, dirs, files in os.walk(self.workspace_root):
                    dirs[:] = [d for d in dirs if d not in self.indexer.ignored_dirs]
                    for f in files:
                        if f.endswith((".py", ".json", ".md", ".ps1", ".yml")):
                            full_f = os.path.join(root, f)
                            try:
                                with open(full_f, "r", encoding="utf-8", errors="ignore") as fp:
                                    for idx, line in enumerate(fp, 1):
                                        if query in line.lower():
                                            rel = os.path.relpath(full_f, self.workspace_root)
                                            matches.append(f"{rel}:{idx}: {line.strip()}")
                                            if len(matches) >= 30:
                                                return "\n".join(matches)
                            except Exception:
                                continue
                return "\n".join(matches) if matches else "No matches found."

            elif tool_name == "find_files":
                import fnmatch
                pat = args.get("pattern", "*")
                found = []
                for root, dirs, files in os.walk(self.workspace_root):
                    dirs[:] = [d for d in dirs if d not in self.indexer.ignored_dirs]
                    for f in files:
                        if fnmatch.fnmatch(f, pat):
                            found.append(os.path.relpath(os.path.join(root, f), self.workspace_root))
                            if len(found) >= 40:
                                return "\n".join(found)
                return "\n".join(found) if found else "No files found."

            elif tool_name == "read_file":
                path = args.get("path", "")
                full_path = path if os.path.isabs(path) else os.path.join(self.workspace_root, path)
                with open(full_path, "r", encoding="utf-8", errors="ignore") as f:
                    return f.read()

            elif tool_name == "read_file_slice":
                path = args.get("path", "")
                full_path = path if os.path.isabs(path) else os.path.join(self.workspace_root, path)
                start = int(args.get("start_line", 1))
                end = int(args.get("end_line", 100))
                with open(full_path, "r", encoding="utf-8", errors="ignore") as f:
                    lines = f.readlines()
                return "".join(lines[max(0, start - 1):end])

            elif tool_name == "write_file":
                path = args.get("path", "")
                content = args.get("content", "")
                return self.patcher.write_file(path, content)

            elif tool_name == "apply_patch":
                return self.patcher.apply_search_replace(
                    rel_path=args.get("path", ""),
                    search_block=args.get("search", ""),
                    replace_block=args.get("replace", "")
                )

            elif tool_name == "run_test_file":
                test_path = args.get("test_path") or args.get("path", "")
                import sys
                res = subprocess.run(
                    [sys.executable, "-m", "pytest", "-q", test_path],
                    cwd=self.workspace_root,
                    capture_output=True,
                    text=True,
                    timeout=120
                )
                output = res.stdout + "\n" + res.stderr
                return output.strip() or "[SUCCESS] Tests completed with no output."

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

