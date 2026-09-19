from __future__ import annotations

import ast
import json
import sys
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))
EXCLUDED_DIRS = {"audit", "tests", "snapshot", "snapshots", "backup", "backups", "old", "archive", ".venv", "venv", "__pycache__", ".pytest_cache", ".git", "tools"}

def inspect_ollama_sync_bodies() -> dict[str, Any]:
    p = PROJECT_ROOT / "runtime" / "models" / "ollama_sync.py"
    if not p.exists():
        return {"exists": False}

    try:
        content = p.read_text(encoding="utf-8", errors="replace")
        tree = ast.parse(content, filename=str(p))

        bodies = {}
        lines = content.splitlines()

        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                start = node.lineno - 1
                end = getattr(node, 'end_lineno', start + 40)
                bodies[node.name] = "\n".join(lines[start:end])

        return {
            "exists": True,
            "bodies": bodies
        }
    except Exception as e:
        return {"exists": True, "error": str(e)}

def main():
    print("=" * 80)
    print(" GATE — OLLAMA SYNC BODIES FORENSICS")
    print("=" * 80)
    print(f"[RACINE] {PROJECT_ROOT}\n")

    res = inspect_ollama_sync_bodies()

    for func_name, src in res.get("bodies", {}).items():
        print(f"--- Fonction : {func_name} ---\n{src}\n")

    print("=" * 80)
    print(" BILAN DE L'EXTRACTION DE OLLAMA SYNC")
    print("================================================================================")
    print("  - Analyse statique réalisée en lecture seule.")
    print("  - Aucune modification de code n'a été effectuée.")
    print("================================================================================")

    out_file = PROJECT_ROOT / "tools" / "ollama_sync_bodies_report.json"
    with open(out_file, "w", encoding="utf-8") as f:
        json.dump(res, f, indent=2)
    print(f"\n[+] Rapport exporté : {out_file}")
    print("=" * 80)

if __name__ == "__main__":
    main()
