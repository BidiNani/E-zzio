"""E-ZZIO Coding Agent — Codebase Structure Indexer."""
from __future__ import annotations
import os
from typing import List, Dict

class CodebaseIndexer:
    def __init__(self, workspace_root: str):
        self.workspace_root = workspace_root
        self.ignored_dirs = {".venv", ".git", "__pycache__", "audit", "state", "artifacts", ".trae", ".vscode"}

    def get_file_tree(self, max_depth: int = 3) -> List[str]:
        """Génère un arbre textuel propre du dépôt pour l'agent."""
        tree = []
        for root, dirs, files in os.walk(self.workspace_root):
            # Filtrer les dossiers ignorés en modifiant dirs sur place
            dirs[:] = [d for d in dirs if d not in self.ignored_dirs]
            
            rel_path = os.path.relpath(root, self.workspace_root)
            depth = 0 if rel_path == "." else rel_path.count(os.sep) + 1
            
            if depth > max_depth:
                continue

            indent = "    " * depth
            if rel_path != ".":
                tree.append(f"{indent}📂 {os.path.basename(root)}/")
            
            sub_indent = "    " * (depth + 1)
            for file in files:
                if file.endswith((".py", ".json", ".md", ".ps1", ".yml")):
                    tree.append(f"{sub_indent}📄 {file}")
                    
        return tree

    def get_compact_map(self) -> str:
        """Renvoie une cartographie compacte du projet pour le system prompt."""
        lines = self.get_file_tree(max_depth=2)
        return "\n".join(lines)
