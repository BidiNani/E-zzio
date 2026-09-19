from __future__ import annotations

import ast
import json
import sys
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))
EXCLUDED_DIRS = {"audit", "tests", "snapshot", "snapshots", "backup", "backups", "old", "archive", ".venv", "venv", "__pycache__", ".pytest_cache", ".git", "tools"}

def inspect_fabric_discovery_calls() -> list[dict[str, Any]]:
    fabric_path = PROJECT_ROOT / "core" / "models" / "fabric.py"
    if not fabric_path.exists():
        return []

    try:
        content = fabric_path.read_text(encoding="utf-8", errors="replace")
        tree = ast.parse(content, filename=str(fabric_path))
        calls = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Call):
                func = node.func
                if isinstance(func, ast.Attribute):
                    calls.append(func.attr)
                elif isinstance(func, ast.Name):
                    calls.append(func.id)
        return [{"fabric_calls_found": list(set(calls))}]
    except Exception as e:
        return [{"error": str(e)}]

def main():
    print("=" * 80)
    print(" GATE — FABRIC CALLS FORENSICS")
    print("=" * 80)
    print(f"[RACINE] {PROJECT_URL if 'PROJECT_URL' in locals() else PROJECT_ROOT}\n")

    res = inspect_fabric_discovery_calls()
    print("[1] Analyse des appels internes dans fabric.py :")
    print(json.dumps(res, indent=2))

    print("\n" + "=" * 80)
    print(" BILAN FINAL FORENSIQUE")
    print("================================================================================")
    print("  - Aucune modification de code ou écriture de registre n'a été effectuée.")
    print("  - Baseline intacte.")
    print("================================================================================")

    out_file = PROJECT_ROOT / "tools" / "fabric_calls_report.json"
    with open(out_file, "w", encoding="utf-8") as f:
        json.dump(res, f, indent=2)
    print(f"\n[+] Rapport exporté : {out_file}")
    print("=" * 80)

if __name__ == "__main__":
    main()
