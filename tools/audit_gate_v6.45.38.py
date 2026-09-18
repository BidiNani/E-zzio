from __future__ import annotations

import ast
import json
import sys
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[1]
EXCLUDED_DIRS = {"audit", "snapshot", "snapshots", "backup", "backups", "old", "archive", ".venv", "venv", "__pycache__", ".pytest_cache", ".git", "tests"}

class OllamaProviderVisitor(ast.NodeVisitor):
    def __init__(self, rel_path: str):
        self.rel_path = rel_path
        self.provider_nodes: list[dict[str, Any]] = []

    def visit_ClassDef(self, node: ast.ClassDef):
        if "OllamaProvider" in node.name:
            class_code = ast.unparse(node)
            self.provider_nodes.append({
                "file": self.rel_path,
                "class": node.name,
                "line": node.lineno,
                "code": class_code
            })
        self.generic_visit(node)

def main():
    print("=" * 80)
    print(" GATE v6.45.38 — OLLAMA PROVIDER TERMINAL TRANSPORT FORENSICS")
    print("=" * 80)
    print(f"[RACINE] {PROJECT_ROOT}\n")

    py_files = [p for p in PROJECT_ROOT.glob("**/*.py") if not (set(p.parts) & EXCLUDED_DIRS)]
    found_providers = []

    for path in py_files:
        rel_path = str(path.relative_to(PROJECT_ROOT))
        if "ollama" not in rel_path.lower():
            continue
        try:
            content = path.read_text(encoding="utf-8", errors="replace")
            tree = ast.parse(content, filename=rel_path)
            visitor = OllamaProviderVisitor(rel_path)
            visitor.visit(tree)
            found_providers.extend(visitor.provider_nodes)
        except Exception as e:
            print(f"[WARN] Erreur parsing {rel_path} : {e}", file=sys.stderr)

    print(f"[+] Classes OllamaProvider trouvées : {len(found_providers)}\n")

    for item in found_providers:
        print("=" * 80)
        print(f" FICHIER : {item['file']} | CLASS : {item['class']} (ligne {item['line']})")
        print("=" * 80)
        print(item['code'])
        print("\n")

    out_file = PROJECT_ROOT / "tools" / "gate_v6_45_38_report.json"
    with open(out_file, "w", encoding="utf-8") as f:
        json.dump(found_providers, f, indent=2)
    print(f"[+] Rapport JSON complet exporté : {out_file}")
    print("=" * 80)

if __name__ == "__main__":
    main()
