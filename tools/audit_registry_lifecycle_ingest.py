from __future__ import annotations

import ast
import json
import sys
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))
EXCLUDED_DIRS = {"audit", "tests", "snapshot", "snapshots", "backup", "backups", "old", "archive", ".venv", "venv", "__pycache__", ".pytest_cache", ".git", "tools"}

def inspect_registry_and_lifecycle() -> dict[str, Any]:
    targets = [
        PROJECT_ROOT / "core" / "models" / "registry.py",
        PROJECT_ROOT / "core" / "models" / "lifecycle.py",
        PROJECT_ROOT / "core" / "models" / "fabric.py"
    ]

    results = {}
    for path in targets:
        if not path.exists():
            continue
        rel_path = str(path.relative_to(PROJECT_ROOT))
        try:
            content = path.read_text(encoding="utf-8", errors="replace")
            tree = ast.parse(content, filename=str(path))
            lines = content.splitlines()

            extracted = {}
            for node in ast.walk(tree):
                if isinstance(node, (ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)):
                    target_names = {"ModelRegistry", "ModelRecord", "ModelLifecycleManager", "ingest_discovery", "upsert", "transition"}
                    if node.name in target_names or any(t in node.name for t in ["ingest", "upsert", "registry", "lifecycle"]):
                        start = node.lineno - 1
                        end = getattr(node, 'end_lineno', start + 45)
                        extracted[node.name] = "\n".join(lines[start:end])

            results[rel_path] = extracted
        except Exception as e:
            results[rel_path] = {"error": str(e)}

    return results

def main():
    print("=" * 80)
    print(" GATE — REGISTRY & LIFECYCLE INGESTION FORENSICS")
    print("=" * 80)
    print(f"[RACINE] {PROJECT_ROOT}\n")

    res = inspect_registry_and_lifecycle()

    for path, items in res.items():
        print(f"=== Module : {path} ===")
        for name, src in items.items():
            print(f"\n--- Élément : {name} ---\n{src}\n")

    print("=" * 80)
    print(" BILAN DE L'INSPECTION DU REGISTRE ET DU LIFECYCLE")
    print("================================================================================")
    print("  - Analyse statique réalisée en lecture seule.")
    print("  - Aucune modification de code n'a été effectuée.")
    print("================================================================================")

    out_file = PROJECT_ROOT / "tools" / "registry_lifecycle_ingest_report.json"
    with open(out_file, "w", encoding="utf-8") as f:
        json.dump(res, f, indent=2)
    print(f"\n[+] Rapport exporté : {out_file}")
    print("=" * 80)

if __name__ == "__main__":
    main()
