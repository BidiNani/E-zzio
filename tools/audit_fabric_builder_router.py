from __future__ import annotations
import json
import ast
import sys
from pathlib import Path
from typing import Dict, Any, List

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))
EXCLUDED_DIRS = {"audit", "tests", "snapshot", "snapshots", "backup", "backups", "old", "archive", ".venv", "venv", "__pycache__", ".pytest_cache", ".git", "tools"}

def inspect_fabric_builder_and_router() -> Dict[str, Any]:
    fabric_path = PROJECT_ROOT / "core" / "models" / "fabric.py"
    router_path = PROJECT_ROOT / "core" / "models" / "router.py"
    
    results = {}
    
    for label, path in [("fabric", fabric_path), ("router", router_path)]:
        if path.exists():
            try:
                content = path.read_text(encoding="utf-8", errors="replace")
                tree = ast.parse(content, filename=str(path))
                lines = content.splitlines()
                
                methods = {}
                for node in ast.walk(tree):
                    if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                        start = node.lineno - 1
                        end = getattr(node, 'end_lineno', start + 35)
                        methods[node.name] = "\n".join(lines[start:end])
                        
                results[label] = {
                    "exists": True,
                    "methods": methods
                }
            except Exception as e:
                results[label] = {"exists": True, "error": str(e)}
        else:
            results[label] = {"exists": False}
            
    return results

def main():
    print("=" * 80)
    print(" GATE — FABRIC BUILDER & ROUTER ENDPOINTS FORENSICS")
    print("=" * 80)
    print(f"[RACINE] {PROJECT_ROOT}\n")

    res = inspect_fabric_builder_and_router()

    for label, data in res.items():
        print(f"=== Module : {label} ===")
        for mname, src in data.get("methods", {}).items():
            print(f"\n--- Méthode : {mname} ---\n{src}\n")

    print("=" * 80)
    print(" BILAN DE L'INSPECTION DE LA FABRIC ET DU ROUTER")
    print("================================================================================")
    print("  - Analyse statique réalisée en lecture seule.")
    print("  - Aucune modification de code n'a été effectuée.")
    print("================================================================================")

    out_file = PROJECT_ROOT / "tools" / "fabric_builder_router_report.json"
    with open(out_file, "w", encoding="utf-8") as f:
        json.dump(res, f, indent=2)
    print(f"\n[+] Rapport exporté : {out_file}")
    print("=" * 80)

if __name__ == "__main__":
    main()