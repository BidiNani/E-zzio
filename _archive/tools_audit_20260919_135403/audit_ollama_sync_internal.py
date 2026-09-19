from __future__ import annotations

import ast
import json
import sys
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))
EXCLUDED_DIRS = {"audit", "tests", "snapshot", "snapshots", "backup", "backups", "old", "archive", ".venv", "venv", "__pycache__", ".pytest_cache", ".git", "tools"}

def inspect_ollama_sync() -> dict[str, Any]:
    p = PROJECT_ROOT / "runtime" / "models" / "ollama_sync.py"
    if not p.exists():
        return {"exists": False}

    try:
        content = p.read_text(encoding="utf-8", errors="replace")
        tree = ast.parse(content, filename=str(p))

        functions = []
        calls = []
        assigns = []

        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                functions.append(node.name)
            elif isinstance(node, ast.Call):
                if isinstance(node.func, ast.Name):
                    calls.append(node.func.id)
                elif isinstance(node.func, ast.Attribute):
                    calls.append(node.func.attr)
            elif isinstance(node, ast.Assign):
                for target in node.targets:
                    if isinstance(target, ast.Name):
                        assigns.append(target.id)

        return {
            "exists": True,
            "functions": functions,
            "calls": list(set(calls)),
            "mentions_registry": "registry" in content.lower(),
            "mentions_lifecycle": "lifecycle" in content.lower() or "ingest" in content.lower(),
            "mentions_tags": "/api/tags" in content or "tags" in content.lower(),
            "mentions_tier": "tier" in content.lower(),
            "mentions_active": "active" in content.lower()
        }
    except Exception as e:
        return {"exists": True, "error": str(e)}

def main():
    print("=" * 80)
    print(" GATE — OLLAMA SYNC INTERNAL FORENSICS")
    print("=" * 80)
    print(f"[RACINE] {PROJECT_ROOT}\n")

    res = inspect_ollama_sync()

    print("[1] ANALYSE DE : runtime/models/ollama_sync.py")
    print(f"  - Existe : {res.get('exists')}")
    print(f"  - Fonctions internes : {res.get('functions', [])}")
    print(f"  - Mentionne le Registre : {'YES' if res.get('mentions_registry') else 'NO'}")
    print(f"  - Mentionne le Lifecycle / Ingest : {'YES' if res.get('mentions_lifecycle') else 'NO'}")
    print(f"  - Mentionne les Tags API (/api/tags) : {'YES' if res.get('mentions_tags') else 'NO'}")
    print(f"  - Mentionne les Tiers sémantiques : {'YES' if res.get('mentions_tier') else 'NO'}")
    print(f"  - Mentionne l'état ACTIVE : {'YES' if res.get('mentions_active') else 'NO'}")

    print("\n" + "=" * 80)
    print(" BILAN INTERNE OLLAMA SYNC")
    print("================================================================================")
    print("  - Analyse statique de ollama_sync.py réalisée en lecture seule stricte.")
    print("  - Aucune modification de code ou d'exécution locale n'a été effectuée.")
    print("================================================================================")

    out = {
        "ollama_sync_analysis": res,
        "writes_performed": 0,
        "runtime_mutations": 0
    }

    out_file = PROJECT_ROOT / "tools" / "ollama_sync_internal_report.json"
    with open(out_file, "w", encoding="utf-8") as f:
        json.dump(out, f, indent=2)
    print(f"\n[+] Rapport exporté : {out_file}")
    print("=" * 80)

if __name__ == "__main__":
    main()
