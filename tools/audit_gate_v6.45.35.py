from __future__ import annotations

import ast
import json
import sys
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[1]
EXCLUDED_DIRS = {"audit", "snapshot", "snapshots", "backup", "backups", "old", "archive", ".venv", "venv", "__pycache__", ".pytest_cache", ".git", "tests"}

class DeepForensicVisitor(ast.NodeVisitor):
    def __init__(self, rel_path: str):
        self.rel_path = rel_path
        self.target_code_extracts: list[dict[str, Any]] = []

    def visit_ClassDef(self, node: ast.ClassDef):
        if node.name in {"OrganismKernel", "CanonicalIdentity", "HDForge", "EzzioInterface"}:
            for sub in node.body:
                if isinstance(sub, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    if sub.name in {"verify_identity", "__init__", "identity_payload", "build_system_prompt", "handle", "load_identity"}:
                        self.target_code_extracts.append({
                            "file": self.rel_path,
                            "class": node.name,
                            "method": sub.name,
                            "line": sub.lineno,
                            "full_code": ast.unparse(sub)
                        })
        self.generic_visit(node)

    def visit_FunctionDef(self, node: ast.FunctionDef):
        if node.name in {"verify_identity", "identity_payload", "build_system_prompt"}:
            self.target_code_extracts.append({
                "file": self.rel_path,
                "class": "<module_func>",
                "method": node.name,
                "line": node.lineno,
                "full_code": ast.unparse(node)
            })
        self.generic_visit(node)

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef):
        if node.name in {"handle", "verify_identity"}:
            self.target_code_extracts.append({
                "file": self.rel_path,
                "class": "<module_func>",
                "method": node.name,
                "line": node.lineno,
                "full_code": ast.unparse(node)
            })
        self.generic_visit(node)

def main():
    print("=" * 80)
    print(" GATE v6.45.35 — DEEP IDENTITY & HANDLE FORENSIC EXTRACTION")
    print("=" * 80)
    print(f"[RACINE] {PROJECT_ROOT}\n")

    py_files = [p for p in PROJECT_ROOT.glob("**/*.py") if not (set(p.parts) & EXCLUDED_DIRS)]
    extracted_data = []

    for path in py_files:
        rel_path = str(path.relative_to(PROJECT_ROOT))
        try:
            content = path.read_text(encoding="utf-8", errors="replace")
            tree = ast.parse(content, filename=rel_path)
            visitor = DeepForensicVisitor(rel_path)
            visitor.visit(tree)
            extracted_data.extend(visitor.target_code_extracts)
        except Exception as e:
            print(f"[WARN] Erreur parsing {rel_path} : {e}", file=sys.stderr)

    print(f"[+] Extraits ciblés collectés : {len(extracted_data)}\n")

    for item in extracted_data:
        print(f"--- [{item['file']}] class {item['class']} -> def {item['method']}() (ligne {item['line']}) ---")
        # Affichage propre limité aux 400 premiers caractères pour lisibilité
        code_preview = item['full_code']
        if len(code_preview) > 600:
            code_preview = code_preview[:600] + "\n    # [... troncature du code pour affichage ...]"
        print(f"{code_preview}\n")

    out_file = PROJECT_ROOT / "tools" / "gate_v6_45_35_report.json"
    with open(out_file, "w", encoding="utf-8") as f:
        json.dump(extracted_data, f, indent=2)
    print(f"[+] Rapport JSON complet exporté : {out_file}")
    print("=" * 80)

if __name__ == "__main__":
    main()
