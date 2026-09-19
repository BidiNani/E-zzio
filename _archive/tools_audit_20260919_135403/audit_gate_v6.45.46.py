from __future__ import annotations

import ast
import json
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[1]

def extract_method_code(file_path: Path, target_methods: set[str]) -> dict[str, str]:
    if not file_path.exists():
        return {"error": f"Fichier introuvable: {file_path}"}
    try:
        content = file_path.read_text(encoding="utf-8", errors="replace")
        tree = ast.parse(content, filename=str(file_path))
    except Exception as e:
        return {"error": f"Erreur AST: {str(e)}"}

    extracted = {}
    for stmt in tree.body:
        if isinstance(stmt, ast.ClassDef):
            for item in stmt.body:
                if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef)) and item.name in target_methods:
                    extracted[f"{stmt.name}.{item.name}"] = ast.unparse(item)
        elif isinstance(stmt, (ast.FunctionDef, ast.AsyncFunctionDef)) and stmt.name in target_methods:
            extracted[stmt.name] = ast.unparse(stmt)
    return extracted

def main():
    print("=" * 80)
    print(" GATE v6.45.46 — INTENT-TO-MODEL PROVENANCE FORENSICS")
    print("=" * 80)
    print(f"[RACINE] {PROJECT_ROOT}\n")

    report: dict[str, Any] = {}

    # 1. Inspection de IntentFabricConnector
    connector_path = PROJECT_ROOT / "core" / "intents" / "fabric_connector.py"
    connector_methods = {"resolve_tier", "execute_intent", "__init__"}
    report["fabric_connector"] = extract_method_code(connector_path, connector_methods)

    # 2. Inspection de AutonomousModelFabric
    fabric_path = PROJECT_ROOT / "core" / "models" / "fabric.py"
    fabric_methods = {"_sync_router_with_registry", "activate_qualified", "build_fabric"}
    report["fabric"] = extract_method_code(fabric_path, fabric_methods)

    print("📁 FICHIER : core/intents/fabric_connector.py")
    for name, code in report["fabric_connector"].items():
        print(f"\n--- [ {name} ] ---")
        print(code)

    print("\n" + "=" * 80)
    print("📁 FICHIER : core/models/fabric.py")
    for name, code in report["fabric"].items():
        print(f"\n--- [ {name} ] ---")
        print(code)

    out_file = PROJECT_ROOT / "tools" / "gate_v6_45_46_report.json"
    with open(out_file, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2)
    print(f"\n[+] Rapport d'arbitrage JSON exporté : {out_file}")
    print("=" * 80)

if __name__ == "__main__":
    main()
