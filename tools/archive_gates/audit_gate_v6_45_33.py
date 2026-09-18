from __future__ import annotations

import ast
import json
import sys
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[1]
EXCLUDED_DIRS = {"audit", "snapshot", "snapshots", "backup", "backups", "old", "archive", ".venv", "venv", "__pycache__", ".pytest_cache", ".git", "tests"}

class KernelInterfaceVisitor(ast.NodeVisitor):
    def __init__(self, rel_path: str):
        self.rel_path = rel_path
        self.interface_definitions: list[dict[str, Any]] = []
        self.kernel_calls: list[dict[str, Any]] = []
        self.handle_methods: list[dict[str, Any]] = []

    def visit_ClassDef(self, node: ast.ClassDef):
        for sub in node.body:
            if isinstance(sub, (ast.FunctionDef, ast.AsyncFunctionDef)):
                if sub.name in {"handle", "_get_kernel", "get_organism_status"}:
                    self.handle_methods.append({
                        "file": self.rel_path,
                        "class": node.name,
                        "method": sub.name,
                        "line": sub.lineno,
                        "code": ast.unparse(sub)[:120]
                    })
        self.generic_visit(node)

    def visit_FunctionDef(self, node: ast.FunctionDef):
        self._inspect_func(node)

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef):
        self._inspect_func(node)

    def _inspect_func(self, node: ast.FunctionDef | ast.AsyncFunctionDef):
        for child in ast.walk(node):
            if isinstance(child, ast.Call):
                call_str = ast.unparse(child.func)
                if "_get_kernel" in call_str or "handle" in call_str:
                    self.kernel_calls.append({
                        "file": self.rel_path,
                        "function": node.name,
                        "call": call_str,
                        "line": child.lineno
                    })
        self.generic_visit(node)

def main():
    print("=" * 80)
    print(" GATE v6.45.33 — KERNEL, INTERFACE & IDENTITY PROVENANCE TRACE")
    print("=" * 80)
    print(f"[RACINE] {PROJECT_ROOT}\n")

    py_files = [p for p in PROJECT_ROOT.glob("**/*.py") if not (set(p.parts) & EXCLUDED_DIRS)]

    all_methods = []
    all_calls = []

    for path in py_files:
        rel_path = str(path.relative_to(PROJECT_ROOT))
        try:
            content = path.read_text(encoding="utf-8", errors="replace")
            tree = ast.parse(content, filename=rel_path)
            visitor = KernelInterfaceVisitor(rel_path)
            visitor.visit(tree)
            all_methods.extend(visitor.handle_methods)
            all_calls.extend(visitor.kernel_calls)
        except Exception as e:
            print(f"[WARN] Erreur parsing {rel_path} : {e}", file=sys.stderr)

    print("[1] MÉTHODES CLÉS DÉTECTÉES (handle / _get_kernel / get_organism_status)")
    for m in all_methods:
        print(f"  • [{m['file']}] class {m['class']} -> def {m['method']}() (ligne {m['line']})")
        print(f"    Extrait : {m['code']}...\n")

    print(f"\n[2] APPELS INTERNES DÉTECTÉS ({len(all_calls)} occurrences)")
    for c in all_calls[:15]:
        print(f"  • [{c['file']}] dans {c['function']}() -> {c['call']} (ligne {c['line']})")

    out_file = PROJECT_ROOT / "tools" / "gate_v6_45_33_report.json"
    with open(out_file, "w", encoding="utf-8") as f:
        json.dump({"methods": all_methods, "calls": all_calls}, f, indent=2)
    print(f"\n[+] Rapport JSON exporté : {out_file}")
    print("=" * 80)

if __name__ == "__main__":
    main()
