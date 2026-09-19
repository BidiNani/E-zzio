from __future__ import annotations

import ast
import json
import sys
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[1]
EXCLUDED_DIRS = {"audit", "snapshot", "snapshots", "backup", "backups", "old", "archive", ".venv", "venv", "__pycache__", ".pytest_cache", ".git", "tests"}

class ConsumerVisitor(ast.NodeVisitor):
    def __init__(self, rel_path: str):
        self.rel_path = rel_path
        self.usages: list[dict[str, Any]] = []

    def visit_ImportFrom(self, node: ast.ImportFrom):
        if node.module and any(k in node.module for k in {"cognitive_router", "models.fabric", "models.registry"}):
            self.usages.append({
                "file": self.rel_path,
                "line": node.lineno,
                "type": "IMPORT",
                "code": ast.unparse(node)
            })
        self.generic_visit(node)

    def visit_Call(self, node: ast.Call):
        call_code = ast.unparse(node.func)
        if any(target in call_code for target in {"CognitiveTaskClassifier", "classify", "get_model", "resolve_model", "select_model"}):
            self.usages.append({
                "file": self.rel_path,
                "line": node.lineno,
                "type": "CALL",
                "code": ast.unparse(node)
            })
        self.generic_visit(node)

    def visit_Attribute(self, node: ast.Attribute):
        if node.attr in {"TASK_MAP", "preferred_model"}:
            self.usages.append({
                "file": self.rel_path,
                "line": node.lineno,
                "type": "ATTR_ACCESS",
                "code": ast.unparse(node)
            })
        self.generic_visit(node)

def main():
    print("=" * 80)
    print(" GATE v6.45.43 — MODEL AUTHORITY CONSUMER FORENSICS")
    print("=" * 80)
    print(f"[RACINE] {PROJECT_ROOT}\n")

    py_files = [p for p in PROJECT_ROOT.glob("**/*.py") if not (set(p.parts) & EXCLUDED_DIRS)]
    all_usages = []

    for path in py_files:
        rel_path = str(path.relative_to(PROJECT_ROOT))
        try:
            content = path.read_text(encoding="utf-8", errors="replace")
            if any(term in content for term in {"CognitiveTaskClassifier", "preferred_model", "TASK_MAP"}):
                tree = ast.parse(content, filename=rel_path)
                visitor = ConsumerVisitor(rel_path)
                visitor.visit(tree)
                all_usages.extend(visitor.usages)
        except Exception as e:
            print(f"[WARN] Erreur parsing {rel_path} : {e}", file=sys.stderr)

    print(f"[+] Consommateurs et références détectés : {len(all_usages)}\n")
    for u in all_usages:
        print(f"  • [{u['file']} (ligne {u['line']})] ({u['type']})")
        print(f"    {u['code']}\n")

    out_file = PROJECT_ROOT / "tools" / "gate_v6_45_43_report.json"
    with open(out_file, "w", encoding="utf-8") as f:
        json.dump(all_usages, f, indent=2)
    print(f"[+] Rapport JSON complet exporté : {out_file}")
    print("=" * 80)

if __name__ == "__main__":
    main()
