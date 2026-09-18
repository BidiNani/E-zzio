from __future__ import annotations

import ast
import json
import sys
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[1]
EXCLUDED_DIRS = {"audit", "snapshot", "snapshots", "backup", "backups", "old", "archive", ".venv", "venv", "__pycache__", ".pytest_cache", ".git", "tests"}

class FullKernelVisitor(ast.NodeVisitor):
    def __init__(self, rel_path: str):
        self.rel_path = rel_path
        self.full_methods: list[dict[str, Any]] = []

    def visit_ClassDef(self, node: ast.ClassDef):
        if node.name == "OrganismKernel":
            for sub in node.body:
                if isinstance(sub, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    # Extraction intégrale de toutes les méthodes majeures du Kernel
                    self.full_methods.append({
                        "file": self.rel_path,
                        "class": node.name,
                        "method": sub.name,
                        "line": sub.lineno,
                        "code": ast.unparse(sub)
                    })
        self.generic_visit(node)

def main():
    print("=" * 80)
    print(" GATE v6.45.37 — FULL KERNEL EXECUTION BODY FORENSICS")
    print("=" * 80)
    print(f"[RACINE] {PROJECT_ROOT}\n")

    py_files = [p for p in PROJECT_ROOT.glob("**/*.py") if not (set(p.parts) & EXCLUDED_DIRS)]
    all_methods = []

    for path in py_files:
        rel_path = str(path.relative_to(PROJECT_ROOT))
        if Path(rel_path).name != "ezzio_kernel.py":
            continue
        try:
            content = path.read_text(encoding="utf-8", errors="replace")
            tree = ast.parse(content, filename=rel_path)
            visitor = FullKernelVisitor(rel_path)
            visitor.visit(tree)
            all_methods.extend(visitor.full_methods)
        except Exception as e:
            print(f"[WARN] Erreur parsing {rel_path} : {e}", file=sys.stderr)

    print(f"[+] Méthodes intégrales extraites de ezzio_kernel.py : {len(all_methods)}\n")

    for item in all_methods:
        print("=" * 80)
        print(f" MÉTHODE : def {item['method']}() (ligne {item['line']})")
        print("=" * 80)
        print(item['code'])
        print("\n")

    out_file = PROJECT_ROOT / "tools" / "gate_v6_45_37_report.json"
    with open(out_file, "w", encoding="utf-8") as f:
        json.dump(all_methods, f, indent=2)
    print(f"[+] Rapport JSON complet exporté : {out_file}")
    print("=" * 80)

if __name__ == "__main__":
    main()
