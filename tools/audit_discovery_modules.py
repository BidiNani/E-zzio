from __future__ import annotations

import ast
import json
import sys
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))
EXCLUDED_DIRS = {"audit", "tests", "snapshot", "snapshots", "backup", "backups", "old", "archive", ".venv", "venv", "__pycache__", ".pytest_cache", ".git", "tools"}

def inspect_discovery_modules() -> dict[str, Any]:
    discovery_dir = PROJECT_ROOT / "core" / "models" / "discovery"
    results = {}

    if discovery_dir.exists() and discovery_dir.is_dir():
        for p in discovery_dir.glob("**/*.py"):
            rel = str(p.relative_to(PROJECT_ROOT))
            try:
                content = p.read_text(encoding="utf-8", errors="replace")
                tree = ast.parse(content, filename=str(p))
                classes = [n.name for n in ast.walk(tree) if isinstance(n, ast.ClassDef)]
                functions = [n.name for n in ast.walk(tree) if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))]
                results[rel] = {
                    "classes": classes,
                    "functions": functions
                }
            except Exception as e:
                results[rel] = {"error": str(e)}
    else:
        results["discovery_dir"] = "Not found"

    # Chercher aussi partout ailleurs des fichiers contenant 'discovery'
    other_discovery = []
    for p in PROJECT_ROOT.glob("**/*.py"):
        if set(p.parts) & EXCLUDED_DIRS:
            continue
        if "discovery" in p.name.lower():
            other_discovery.append(str(p.relative_to(PROJECT_ROOT)))

    return {
        "discovery_folder_files": results,
        "other_discovery_files": other_discovery
    }

def main():
    print("=" * 80)
    print(" GATE — DISCOVERY MODULES FORENSICS")
    print("=" * 80)
    print(f"[RACINE] {PROJECT_ROOT}\n")

    res = inspect_discovery_modules()

    print("[1] Fichiers dans core/models/discovery/ :")
    disc = res.get("discovery_folder_files", {})
    if isinstance(disc, dict) and disc:
        for k, v in disc.items():
            print(f"  - {k} : {v}")
    else:
        print("  - Aucun ou répertoire introuvable.")

    print("\n[2] Autres fichiers contenant 'discovery' dans le nom :")
    for o in res.get("other_discovery_files", []):
        print(f"  - {o}")

    print("\n" + "=" * 80)
    print(" BILAN DE L'INSPECTION DES MODULES DE DÉCOUVERTE")
    print("================================================================================")
    print("  - Analyse statique réalisée en lecture seule.")
    print("  - Aucune modification de code n'a été effectuée.")
    print("================================================================================")

    out_file = PROJECT_ROOT / "tools" / "discovery_modules_report.json"
    with open(out_file, "w", encoding="utf-8") as f:
        json.dump(res, f, indent=2)
    print(f"\n[+] Rapport exporté : {out_file}")
    print("=" * 80)

if __name__ == "__main__":
    main()
