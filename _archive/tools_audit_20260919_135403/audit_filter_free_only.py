from __future__ import annotations

import ast
import json
import sys
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))
EXCLUDED_DIRS = {"audit", "tests", "snapshot", "snapshots", "backup", "backups", "old", "archive", ".venv", "venv", "__pycache__", ".pytest_cache", ".git", "tools"}

def inspect_filter_free_only() -> dict[str, Any]:
    filter_files = []
    for p in PROJECT_ROOT.glob("**/*.py"):
        if set(p.parts) & EXCLUDED_DIRS:
            continue
        try:
            content = p.read_text(encoding="utf-8", errors="replace")
            if "filter_free_only" in content or "policy_allows" in content:
                filter_files.append(p)
        except Exception:
            continue

    results = {}
    for path in filter_files:
        rel_path = str(path.relative_to(PROJECT_ROOT))
        try:
            content = path.read_text(encoding="utf-8", errors="replace")
            tree = ast.parse(content, filename=str(path))
            lines = content.splitlines()

            functions = {}
            for node in ast.walk(tree):
                if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and any(term in node.name for term in ["filter", "policy", "free"]):
                    start = node.lineno - 1
                    end = getattr(node, 'end_lineno', start + 30)
                    functions[node.name] = "\n".join(lines[start:end])

            results[rel_path] = functions
        except Exception as e:
            results[rel_path] = {"error": str(e)}

    return results

def main():
    print("=" * 80)
    print(" GATE — FILTER FREE ONLY CONTRACT FORENSICS")
    print("=" * 80)
    print(f"[RACINE] {PROJECT_ROOT}\n")

    res = inspect_filter_free_only()

    for path, funcs in res.items():
        print(f"[FICHIER] {path}")
        for fname, src in funcs.items():
            print(f"\n--- Fonction : {fname} ---\n{src}\n")

    print("=" * 80)
    print(" BILAN DE L'INSPECTION DU FILTRE DE GRATUITÉ")
    print("================================================================================")
    print("  - Analyse statique réalisée en lecture seule.")
    print("  - Aucune modification de code n'a été effectuée.")
    print("================================================================================")

    out_file = PROJECT_ROOT / "tools" / "filter_free_only_contract_report.json"
    with open(out_file, "w", encoding="utf-8") as f:
        json.dump(res, f, indent=2)
    print(f"\n[+] Rapport exporté : {out_file}")
    print("=" * 80)

if __name__ == "__main__":
    main()
