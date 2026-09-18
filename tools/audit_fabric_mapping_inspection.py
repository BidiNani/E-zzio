from __future__ import annotations

import ast
import json
import sys
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))
EXCLUDED_DIRS = {"audit", "tests", "snapshot", "snapshots", "backup", "backups", "old", "archive", ".venv", "venv", "__pycache__", ".pytest_cache", ".git", "tools"}

def inspect_fabric_internals() -> dict[str, Any]:
    fabric_path = PROJECT_ROOT / "core" / "models" / "fabric.py"
    if not fabric_path.exists():
        return {"exists": False}

    try:
        content = fabric_path.read_text(encoding="utf-8", errors="replace")
        tree = ast.parse(content, filename=str(fabric_path))

        qualify_sources = []
        activate_sources = []

        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                if node.name == "qualify_candidates":
                    for sub in ast.walk(node):
                        if isinstance(sub, ast.Attribute) and isinstance(sub.value, ast.Name) and sub.value.id == "self":
                            qualify_sources.append(sub.attr)
                elif node.name == "activate_qualified":
                    for sub in ast.walk(node):
                        if isinstance(sub, ast.Subscript) and isinstance(sub.slice, ast.Constant):
                            activate_sources.append(sub.slice.value)
                        elif isinstance(sub, ast.Constant):
                            if isinstance(sub.value, str):
                                activate_sources.append(sub.value)

        return {
            "exists": True,
            "qualify_attributes": list(set(qualify_sources)),
            "activate_string_keys": list(set(activate_sources))
        }
    except Exception as e:
        return {"exists": True, "error": str(e)}

def main():
    print("=" * 80)
    print(" GATE — FABRIC MAPPING INSPECTION")
    print("=" * 80)
    print(f"[RACINE] {PROJECT_ROOT}\n")

    res = inspect_fabric_internals()

    print("[1] Attributs accédés par qualify_candidates() sur self :")
    print(res.get("qualify_attributes", []))

    print("\n[2] Clés string recherchées par activate_qualified() dans les résultats :")
    print(res.get("activate_string_keys", []))

    print("\n" + "=" * 80)
    print(" BILAN DE L'INSPECTION INTERNE DE LA FABRIC")
    print("================================================================================")
    print("  - Analyse statique terminée sans aucune mutation.")
    print("================================================================================")

    out_file = PROJECT_ROOT / "tools" / "fabric_mapping_inspection_report.json"
    with open(out_file, "w", encoding="utf-N") as f:
        json.dump(res, f, indent=2)
    print(f"\n[+] Rapport exporté : {out_file}")
    print("=" * 80)

if __name__ == "__main__":
    main()
