from __future__ import annotations
import ast
import json
import sys
from pathlib import Path
from typing import Any, Dict, List

PROJECT_ROOT = Path(__file__).resolve().parents[1]
EXCLUDED_DIRS = {"audit", "snapshot", "snapshots", "backup", "backups", "old", "archive", ".venv", "venv", "__pycache__", ".pytest_cache", ".git", "tests"}

TARGET_FILES = [
    "core/models/registry.py",
    "core/models/fabric.py",
    "core/models/lifecycle.py",
    "core/intents/fabric_connector.py"
]

class FabricContractVisitor(ast.NodeVisitor):
    def __init__(self, rel_path: str):
        self.rel_path = rel_path
        self.classes: List[Dict[str, Any]] = []
        self.functions: List[Dict[str, Any]] = []

    def visit_ClassDef(self, node: ast.ClassDef):
        methods = []
        for item in node.body:
            if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef)):
                args = [a.arg for a in item.args.args]
                returns = ast.unparse(item.returns) if item.returns else "None"
                methods.append({
                    "name": item.name,
                    "line": item.lineno,
                    "args": args,
                    "returns": returns,
                    "docstring": ast.get_docstring(item) or ""
                })
        self.classes.append({
            "name": node.name,
            "line": node.lineno,
            "docstring": ast.get_docstring(node) or "",
            "methods": methods
        })
        self.generic_visit(node)

    def visit_FunctionDef(self, node: ast.FunctionDef):
        if not any(node.name in [m["name"] for c in self.classes for m in c["methods"]]):
            args = [a.arg for a in node.args.args]
            returns = ast.unparse(node.returns) if node.returns else "None"
            self.functions.append({
                "name": node.name,
                "line": node.lineno,
                "args": args,
                "returns": returns,
                "docstring": ast.get_docstring(node) or ""
            })
        self.generic_visit(node)

def main():
    print("=" * 80)
    print(" GATE v6.45.44 — FABRIC & REGISTRY CONTRACT FORENSICS")
    print("=" * 80)
    print(f"[RACINE] {PROJECT_ROOT}\n")

    report: Dict[str, Any] = {}

    for rel_path in TARGET_FILES:
        target_path = PROJECT_ROOT / rel_path
        if not target_path.exists():
            print(f"[WARN] Fichier cible introuvable : {rel_path}")
            continue

        try:
            content = target_path.read_text(encoding="utf-8", errors="replace")
            tree = ast.parse(content, filename=rel_path)
            visitor = FabricContractVisitor(rel_path)
            visitor.visit(tree)
            report[rel_path] = {
                "classes": visitor.classes,
                "functions": visitor.functions
            }
        except Exception as e:
            print(f"[WARN] Erreur parsing {rel_path} : {e}", file=sys.stderr)

    for file, data in report.items():
        print(f"\n📁 FICHIER : {file}")
        for cls in data["classes"]:
            print(f"  🏛️  CLASS {cls['name']} (ligne {cls['line']})")
            for m in cls["methods"]:
                args_str = ", ".join(m["args"])
                print(f"      • {m['name']}({args_str}) -> {m['returns']}")
        for fn in data["functions"]:
            args_str = ", ".join(fn["args"])
            print(f"  ⚙️  FUNCTION {fn['name']}({args_str}) -> {fn['returns']}")

    out_file = PROJECT_ROOT / "tools" / "gate_v6_45_44_report.json"
    with open(out_file, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2)
    print(f"\n[+] Rapport d'arbitrage JSON exporté : {out_file}")
    print("=" * 80)

if __name__ == "__main__":
    main()