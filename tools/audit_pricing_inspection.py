from __future__ import annotations

import ast
import json
import sys
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))
EXCLUDED_DIRS = {"audit", "tests", "snapshot", "snapshots", "backup", "backups", "old", "archive", ".venv", "venv", "__pycache__", ".pytest_cache", ".git", "tools"}

def inspect_pricing_and_free_only() -> dict[str, Any]:
    free_only_path = PROJECT_ROOT / "core" / "models" / "qualification" / "free_only.py"
    if not free_only_path.exists():
        return {"exists": False}

    try:
        content = free_only_path.read_text(encoding="utf-8", errors="replace")
        tree = ast.parse(content, filename=str(free_only_path))
        lines = content.splitlines()

        funcs = {}
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                start = node.lineno - 1
                end = getattr(node, 'end_lineno', start + 35)
                funcs[node.name] = "\n".join(lines[start:end])

        return {
            "exists": True,
            "functions": funcs
        }
    except Exception as e:
        return {"exists": True, "error": str(e)}

def main():
    print("=" * 80)
    print(" GATE — FREE ONLY POLICY & PRICING INSPECTION")
    print("=" * 80)
    print(f"[RACINE] {PROJECT_ROOT}\n")

    res = inspect_pricing_and_free_only()

    for fname, src in res.get("functions", {}).items():
        print(f"--- Fonction : {fname} ---\n{src}\n")

    print("=" * 80)
    print(" BILAN DE L'INSPECTION DU FILTRE DE PRIX")
    print("================================================================================")
    print("  - Analyse statique réalisée en lecture seule.")
    print("  - Aucune modification de code n'a été effectuée.")
    print("================================================================================")

    out_file = PROJECT_ROOT / "tools" / "pricing_inspection_report.json"
    with open(out_file, "w", encoding="utf-8") as f:
        json.dump(res, f, indent=2)
    print(f"\n[+] Rapport exporté : {out_file}")
    print("=" * 80)

if __name__ == "__main__":
    main()
