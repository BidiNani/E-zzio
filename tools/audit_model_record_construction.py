from __future__ import annotations

import ast
import json
import sys
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))
EXCLUDED_DIRS = {"audit", "tests", "snapshot", "snapshots", "backup", "backups", "old", "archive", ".venv", "venv", "__pycache__", ".pytest_cache", ".git", "tools"}

def inspect_record_construction() -> dict[str, Any]:
    registry_path = PROJECT_ROOT / "core" / "models" / "registry.py"
    fabric_path = PROJECT_ROOT / "core" / "models" / "fabric.py"

    results = {}

    for p, name in [(registry_path, "registry"), (fabric_path, "fabric")]:
        if not p.exists():
            continue
        try:
            content = p.read_text(encoding="utf-8", errors="replace")
            tree = ast.parse(content, filename=str(p))

            records_instantiated = []
            decorators = []
            winners_logic = []

            for node in ast.walk(tree):
                if isinstance(node, ast.ClassDef):
                    for dec in node.decorator_list:
                        if isinstance(dec, ast.Name):
                            decorators.append((node.name, dec.id))
                        elif isinstance(dec, ast.Call) and isinstance(dec.func, ast.Name):
                            decorators.append((node.name, dec.func.id))
                elif isinstance(node, ast.Call):
                    if isinstance(node.func, ast.Name) and "Record" in node.func.id:
                        records_instantiated.append(node.func.id)
                    elif isinstance(node.func, ast.Attribute) and "Record" in node.func.attr:
                        records_instantiated.append(node.func.attr)

            if name == "fabric":
                for node in ast.walk(tree):
                    if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                        if "winner" in node.name.lower() or "qualif" in node.name.lower():
                            winners_logic.append(node.name)

            results[name] = {
                "decorators": decorators,
                "records_instantiated": list(set(records_instantiated)),
                "winners_logic": winners_logic
            }
        except Exception as e:
            results[name] = {"error": str(e)}

    return results

def main():
    print("=" * 80)
    print(" GATE — MODEL RECORD CONSTRUCTION & FABRIC CONSUMPTION FORENSICS")
    print("=" * 80)
    print(f"[RACINE] {PROJECT_ROOT}\n")

    res = inspect_record_construction()

    print("[1] ANALYSE DE LA DÉCORATION DE CLASSES (ex: dataclass)")
    print(f"  - Registre / Modèles : {res.get('registry', {}).get('decorators', [])}")

    print("\n[2] LOGIQUE DE SÉLECTION DES WINNERS (Fabric)")
    print(f"  - Fonctions clés : {res.get('fabric', {}).get('winners_logic', [])}")

    print("\n" + "=" * 80)
    print(" BILAN DE CONSTRUCTION ET CONSOMMATION")
    print("================================================================================")
    print("  - Analyse statique de l'instanciation et des flux de la Fabric achevée.")
    print("  - Aucune modification de code n'a été effectuée.")
    print("================================================================================")

    out_file = PROJECT_ROOT / "tools" / "model_record_construction_report.json"
    with open(out_file, "w", encoding="utf-8") as f:
        json.dump(res, f, indent=2)
    print(f"\n[+] Rapport exporté : {out_file}")
    print("=" * 80)

if __name__ == "__main__":
    main()
