from __future__ import annotations

import ast
import json
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[1]
EXCLUDED_DIRS = {"audit", "tests", "snapshot", "snapshots", "backup", "backups", "old", "archive", ".venv", "venv", "__pycache__", ".pytest_cache", ".git"}

class ExecutionChainVisitor(ast.NodeVisitor):
    def __init__(self, rel_path: str):
        self.rel_path = rel_path
        self.imports: list[str] = []
        self.calls: list[str] = []
        self.assignments: list[str] = []

    def visit_Import(self, node: ast.Import):
        for alias in node.names:
            self.imports.append(alias.name)
        self.generic_visit(node)

    def visit_ImportFrom(self, node: ast.ImportFrom):
        mod = node.module or ""
        for alias in node.names:
            self.imports.append(f"{mod}.{alias.name}")
        self.generic_visit(node)

    def visit_Call(self, node: ast.Call):
        call_str = ast.unparse(node.func)
        self.calls.append(call_str)
        self.generic_visit(node)

    def visit_Assign(self, node: ast.Assign):
        target_str = ast.unparse(node.targets)
        if any(k in target_str.lower() for k in {"model", "provider", "selected", "preferred", "route"}):
            self.assignments.append(target_str)
        self.generic_visit(node)

def main():
    print("=" * 80)
    print(" GATE v6.45.47 — END-TO-END ACTIVE RUNTIME EXECUTION TRACE")
    print("=" * 80)
    print(f"[RACINE] {PROJECT_ROOT}\n")

    py_files = [p for p in PROJECT_ROOT.glob("**/*.py") if not (set(p.parts) & EXCLUDED_DIRS)]

    # Cibles prioritaires d'exécution active
    entry_candidates = [
        "runtime/bidi/presence.py",
        "runtime/bidi/ezzio_interface.py",
        "ezzio_kernel.py",
        "core/ezzio_master.py"
    ]

    report: dict[str, Any] = {}

    for rel_path_str in entry_candidates:
        p = PROJECT_ROOT / rel_path_str
        if not p.exists():
            continue
        try:
            content = p.read_text(encoding="utf-8", errors="replace")
            tree = ast.parse(content, filename=rel_path_str)
            visitor = ExecutionChainVisitor(rel_path_str)
            visitor.visit(tree)
            report[rel_path_str] = {
                "imports": list(set(visitor.imports)),
                "calls": list(set(visitor.calls)),
                "decision_assignments": list(set(visitor.assignments))
            }
        except Exception as e:
            print(f"[WARN] Erreur parsing {rel_path_str} : {e}")

    print("[+] Analyse des points d'entrée actifs de production :")
    for file, data in report.items():
        print(f"\n📁 {file}")
        print(f"  • Imports clés : {len(data['imports'])}")
        for imp in data['imports'][:10]:
            print(f"    - import {imp}")
        print(f"  • Appels sortants détectés : {len(data['calls'])}")
        for call in data['calls'][:10]:
            print(f"    - call {call}()")
        print(f"  • Affectations de décision : {data['decision_assignments']}")

    out_file = PROJECT_ROOT / "tools" / "gate_v6_45_47_report.json"
    with open(out_file, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2)
    print(f"\n[+] Rapport d'exécution exporté : {out_file}")
    print("=" * 80)

if __name__ == "__main__":
    main()
