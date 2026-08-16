import os
import sys
import json
import hashlib
import ast
from pathlib import Path
from datetime import datetime

class EzzioAuditScanner:
    def __init__(self, root_dir: Path, output_dir: Path):
        self.root_dir = root_dir.resolve()
        self.output_dir = output_dir.resolve()
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        self.excluded_dirs = {".git", "__pycache__", "venv", "node_modules", "runtime/audit"}
        
        self.inventory = []
        self.python_symbols = {}
        self.imports_graph = {}
        self.configs_inventory = {}

    def is_excluded(self, path: Path) -> bool:
        rel_path = path.relative_to(self.root_dir)
        parts = rel_path.parts
        return any(ex in parts for ex in self.excluded_dirs)

    def scan(self):
        print(f"[*] Démarrage du scan en lecture seule de : {self.root_dir}")
        for path in self.root_dir.rglob("*"):
            if path.is_file():
                if self.is_excluded(path):
                    continue
                rel_path = str(path.relative_to(self.root_dir))
                
                # 1. Analyse de base des fichiers
                file_info = self._inspect_file(path, rel_path)
                self.inventory.append(file_info)

                # 2. Analyse spécifique Python (AST)
                if path.suffix == ".py":
                    self._parse_python(path, rel_path)

                # 3. Analyse spécifique JSON / Configs
                elif path.suffix in [".json", ".jsonl", ".yaml", ".yml"]:
                    self._parse_config(path, rel_path)

        # Sauvegarde des artefacts
        self._save_artifacts()
        print(f"[OK] Scan terminé. {len(self.inventory)} fichiers catalogués dans {self.output_dir}")

    def _inspect_file(self, path: Path, rel_path: str) -> dict:
        stat = path.stat()
        sha256 = hashlib.sha256(path.read_bytes()).hexdigest()
        return {
            "path": rel_path,
            "size_bytes": stat.st_size,
            "extension": path.suffix,
            "modified_at": datetime.fromtimestamp(stat.st_mtime).isoformat(),
            "sha256": sha256
        }

    def _parse_python(self, path: Path, rel_path: str):
        try:
            content = path.read_text(encoding="utf-8")
            tree = ast.parse(content, filename=rel_path)
            
            classes = []
            functions = []
            imports = []

            for node in ast.walk(tree):
                if isinstance(node, ast.ClassDef):
                    classes.append(node.name)
                elif isinstance(node, ast.FunctionDef):
                    functions.append(node.name)
                elif isinstance(node, ast.Import):
                    for alias in node.names:
                        imports.append(alias.name)
                elif isinstance(node, ast.ImportFrom):
                    if node.module:
                        imports.append(node.module)

            self.python_symbols[rel_path] = {
                "classes": classes,
                "functions": functions
            }
            self.imports_graph[rel_path] = list(set(imports))
        except Exception as e:
            self.python_symbols[rel_path] = {"error": str(e)}

    def _parse_config(self, path: Path, rel_path: str):
        try:
            if path.suffix == ".json":
                data = json.loads(path.read_text(encoding="utf-8"))
                keys = list(data.keys()) if isinstance(data, dict) else ["array_root"]
                self.configs_inventory[rel_path] = {"type": "json", "keys": keys}
            else:
                self.configs_inventory[rel_path] = {"type": path.suffix[1:], "status": "raw"}
        except Exception as e:
            self.configs_inventory[rel_path] = {"error": str(e)}

    def _save_artifacts(self):
        (self.output_dir / "inventory.json").write_text(json.dumps(self.inventory, indent=2, ensure_ascii=False), encoding="utf-8")
        (self.output_dir / "python_symbols.json").write_text(json.dumps(self.python_symbols, indent=2, ensure_ascii=False), encoding="utf-8")
        (self.output_dir / "imports_graph.json").write_text(json.dumps(self.imports_graph, indent=2, ensure_ascii=False), encoding="utf-8")
        (self.output_dir / "configs_inventory.json").write_text(json.dumps(self.configs_inventory, indent=2, ensure_ascii=False), encoding="utf-8")

if __name__ == "__main__":
    scanner = EzzioAuditScanner(Path("."), Path("runtime/audit/full_scan"))
    scanner.scan()
