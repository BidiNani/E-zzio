from __future__ import annotations

import ast
import json
import sys
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[1]
EXCLUDED_DIRS = {"audit", "snapshot", "snapshots", "backup", "backups", "old", "archive", ".venv", "venv", "__pycache__", ".pytest_cache", ".git", "tests"}

class ClassifierForensicVisitor(ast.NodeVisitor):
    def __init__(self, rel_path: str):
        self.rel_path = rel_path
        self.classifier_nodes: list[dict[str, Any]] = []

    def visit_ClassDef(self, node: ast.ClassDef):
        if "Classifier" in node.name or "Task" in node.name:
            self.classifier_nodes.append({
                "file": self.rel_path,
                "type": "CLASS",
                "name": node.name,
                "line": node.lineno,
                "code": ast.unparse(node)
            })
        self.generic_visit(node)

    def visit_FunctionDef(self, node: ast.FunctionDef):
        if "classify" in node.name:
            self.classifier_nodes.append({
                "file": self.rel_path,
                "type": "METHOD",
                "name": node.name,
                "line": node.lineno,
                "code": ast.unparse(node)
            })
        self.generic_visit(node)

def main():
    print("=" * 80)
    print(" GATE v6.45.42 — MODEL AUTHORITY ROOT FORENSICS")
    print("=" * 80)
    print(f"[RACINE] {PROJECT_ROOT}\n")

    py_files = [p for p in PROJECT_ROOT.glob("**/*.py") if not (set(p.parts) & EXCLUDED_DIRS)]
    findings = []

    for path in py_files:
        rel_path = str(path.relative_to(PROJECT_ROOT))
        try:
            content = path.read_text(encoding="utf-8", errors="replace")
            if "classify" in content or "classifier" in rel_path.lower():
                tree = ast.parse(content, filename=rel_path)
                visitor = ClassifierForensicVisitor(rel_path)
                visitor.visit(tree)
                findings.extend(visitor.classifier_nodes)
        except Exception as e:
            print(f"[WARN] Erreur parsing {rel_path} : {e}", file=sys.stderr)

    print(f"[+] Artefacts de classification détectés : {len(findings)}")
    for f in findings:
        print(f"\n  • [{f['file']} -> {f['type']} {f['name']} (ligne {f['line']})]")
        snippet = f['code']
        if len(snippet) > 600:
            snippet = snippet[:600] + "\n    # [... troncature affichage ...]"
        print(snippet)

    out_file = PROJECT_ROOT / "tools" / "gate_v6_45_42_report.json"
    with open(out_file, "w", encoding="utf-8") as f:
        json.dump(findings, f, indent=2)
    print(f"\n[+] Rapport d'arbitrage JSON exporté : {out_file}")
    print("=" * 80)

if __name__ == "__main__":
    main()
