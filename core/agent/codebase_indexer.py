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

    def get_repo_map(self, max_files: int = 10) -> str:
        """Cartographie compacte des symboles AST du dépôt."""
        import ast
        symbols = []
        count = 0
        for root, dirs, files in os.walk(self.workspace_root):
            dirs[:] = [d for d in dirs if d not in self.ignored_dirs]
            for file in files:
                if file.endswith(".py"):
                    full_path = os.path.join(root, file)
                    rel_path = os.path.relpath(full_path, self.workspace_root)
                    try:
                        with open(full_path, "r", encoding="utf-8", errors="ignore") as f:
                            tree = ast.parse(f.read(), filename=file)
                        file_symbols = []
                        for node in tree.body:
                            if isinstance(node, ast.FunctionDef):
                                file_symbols.append(f"  def {node.name}()")
                            elif isinstance(node, ast.ClassDef):
                                file_symbols.append(f"  class {node.name}")
                        if file_symbols:
                            symbols.append(f"{rel_path}:\n" + "\n".join(file_symbols))
                            count += 1
                            if count >= max_files:
                                return "\n\n".join(symbols)
                    except Exception:
                        continue
        return "\n\n".join(symbols) if symbols else "def ezzio_main(): pass"
