from __future__ import annotations

import ast
import json
import sys
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[1]
EXCLUDED_DIRS = {"audit", "snapshot", "snapshots", "backup", "backups", "old", "archive", ".venv", "venv", "__pycache__", ".pytest_cache", ".git", "tests"}

class Trace36Visitor(ast.NodeVisitor):
    def __init__(self, rel_path: str):
        self.rel_path = rel_path
        self.extracted_items: list[dict[str, Any]] = []
        self.preferred_model_usages: list[dict[str, Any]] = []

    def visit_ClassDef(self, node: ast.ClassDef):
        if node.name in {"CanonicalIdentity", "OrganismKernel"}:
            for sub in node.body:
                if isinstance(sub, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    if sub.name in {"__init__", "_get_canonical_json", "_verify_integrity", "process_request", "handle_request"}:
                        self.extracted_items.append({
                            "file": self.rel_path,
                            "class": node.name,
                            "method": sub.name,
                            "line": sub.lineno,
                            "code": ast.unparse(sub)
                        })
        self.generic_visit(node)

    def visit_FunctionDef(self, node: ast.FunctionDef):
        self._check_preferred_model(node)
        self.generic_visit(node)

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef):
        self._check_preferred_model(node)
        self.generic_visit(node)

    def _check_preferred_model(self, node: ast.FunctionDef | ast.AsyncFunctionDef):
        for child in ast.walk(node):
            if isinstance(child, ast.Name) and child.id == "preferred_model":
                self.preferred_model_usages.append({
                    "file": self.rel_path,
                    "function": node.name,
                    "line": child.lineno,
                    "snippet": ast.unparse(node)[:300]
                })
                break

def main():
    print("=" * 80)
    print(" GATE v6.45.36 — PROCESS_REQUEST & PREFERRED_MODEL FORENSICS")
    print("=" * 80)
    print(f"[RACINE] {PROJECT_ROOT}\n")

    py_files = [p for p in PROJECT_ROOT.glob("**/*.py") if not (set(p.parts) & EXCLUDED_DIRS)]
    all_extracted = []
    all_usages = []

    for path in py_files:
        rel_path = str(path.relative_to(PROJECT_ROOT))
        try:
            content = path.read_text(encoding="utf-8", errors="replace")
            tree = ast.parse(content, filename=rel_path)
            visitor = Trace36Visitor(rel_path)
            visitor.visit(tree)
            all_extracted.extend(visitor.extracted_items)
            all_usages.extend(visitor.preferred_model_usages)
        except Exception as e:
            print(f"[WARN] Erreur parsing {rel_path} : {e}", file=sys.stderr)

    print(f"[1] MÉTHODES CLÉS EXTRAITES ({len(all_extracted)} blocs)")
    for item in all_extracted:
        print(f"\n--- [{item['file']}] class {item['class']} -> def {item['method']}() (ligne {item['line']}) ---")
        code_snippet = item['code']
        if len(code_snippet) > 800:
            code_snippet = code_snippet[:800] + "\n    # [... troncature affichage ...]"
        print(code_snippet)

    print(f"\n[2] USAGES DE 'preferred_model' DÉTECTÉS ({len(all_usages)} occurrences)")
    for u in all_usages:
        print(f"  • [{u['file']}] dans {u['function']}() (ligne {u['line']})")
        print(f"    Extrait : {u['snippet']}...\n")

    out_file = PROJECT_ROOT / "tools" / "gate_v6_45_36_report.json"
    with open(out_file, "w", encoding="utf-8") as f:
        json.dump({"extracted": all_extracted, "usages": all_usages}, f, indent=2)
    print(f"[+] Rapport JSON exporté : {out_file}")
    print("=" * 80)

if __name__ == "__main__":
    main()
