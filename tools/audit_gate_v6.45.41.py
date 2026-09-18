from __future__ import annotations

import ast
import json
import sys
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[1]
EXCLUDED_DIRS = {"audit", "snapshot", "snapshots", "backup", "backups", "old", "archive", ".venv", "venv", "__pycache__", ".pytest_cache", ".git", "tests"}

TARGET_FILES = {
    "runtime/bidi/presence.py",
    "runtime/bidi/ezzio_interface.py",
    "ezzio_kernel.py",
    "core/providers/ollama_provider.py"
}

class ValueProvenanceVisitor(ast.NodeVisitor):
    def __init__(self, rel_path: str):
        self.rel_path = rel_path
        self.traces: list[dict[str, Any]] = []

    def visit_FunctionDef(self, node: ast.FunctionDef):
        self._inspect_func(node)
        self.generic_visit(node)

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef):
        self._inspect_func(node)
        self.generic_visit(node)

    def _inspect_func(self, node: ast.FunctionDef | ast.AsyncFunctionDef):
        func_name = node.name
        # Recherche d'affectations ou d'appels liés à model / preferred_model / selected_model
        for child in ast.walk(node):
            if isinstance(child, ast.Assign):
                target_code = ast.unparse(child.targets)
                if any(k in target_code for k in {"model", "preferred", "selected", "payload"}):
                    self.traces.append({
                        "file": self.rel_path,
                        "function": func_name,
                        "line": child.lineno,
                        "type": "ASSIGN",
                        "code": ast.unparse(child)
                    })
            elif isinstance(child, ast.Call):
                call_code = ast.unparse(child.func)
                if any(k in call_code for k in {"handle", "process_request", "OllamaProvider", "search", "classify"}):
                    self.traces.append({
                        "file": self.rel_path,
                        "function": func_name,
                        "line": child.lineno,
                        "type": "CALL",
                        "code": ast.unparse(child)
                    })

def main():
    print("=" * 80)
    print(" GATE v6.45.41 — TERMINAL MODEL/PROVIDER VALUE PROVENANCE")
    print("=" * 80)
    print(f"[RACINE] {PROJECT_ROOT}\n")

    all_traces = []

    for rel_path in TARGET_FILES:
        p = PROJECT_ROOT / rel_path
        if not p.exists():
            print(f"[WARN] Fichier cible introuvable : {rel_path}")
            continue
        try:
            content = p.read_text(encoding="utf-8", errors="replace")
            tree = ast.parse(content, filename=rel_path)
            visitor = ValueProvenanceVisitor(rel_path)
            visitor.visit(tree)
            all_traces.extend(visitor.traces)
        except Exception as e:
            print(f"[WARN] Erreur parsing {rel_path} : {e}", file=sys.stderr)

    print(f"[+] Jalons de provenance de valeur extraits : {len(all_traces)}")
    for t in all_traces:
        print(f"\n  • [{t['file']} -> {t['function']}() ligne {t['line']}] ({t['type']})")
        print(f"    {t['code']}")

    out_file = PROJECT_ROOT / "tools" / "gate_v6_45_41_report.json"
    with open(out_file, "w", encoding="utf-8") as f:
        json.dump(all_traces, f, indent=2)
    print(f"\n[+] Rapport d'arbitrage JSON exporté : {out_file}")
    print("=" * 80)

if __name__ == "__main__":
    main()
