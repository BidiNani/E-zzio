from __future__ import annotations
import json
import ast
import sys
from pathlib import Path
from typing import Dict, Any, List

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))
EXCLUDED_DIRS = {"audit", "tests", "snapshot", "snapshots", "backup", "backups", "old", "archive", ".venv", "venv", "__pycache__", ".pytest_cache", ".git", "tools"}

def inspect_fabric_and_qualification() -> Dict[str, Any]:
    fabric_path = PROJECT_ROOT / "core" / "models" / "fabric.py"
    qual_path = PROJECT_ROOT / "EZZIO_Model_Qualification_Gate_v4.2.py"
    
    results = {}
    
    for p, name in [(fabric_path, "fabric"), (qual_path, "qualification")]:
        if not p.exists():
            continue
        try:
            content = p.read_text(encoding="utf-8", errors="replace")
            tree = ast.parse(content, filename=str(p))
            
            method_signatures = {}
            for node in ast.walk(tree):
                if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    args = [arg.arg for arg in node.args.args]
                    returns = ast.unparse(node.returns) if node.returns else "None"
                    method_signatures[node.name] = {
                        "args": args,
                        "returns": returns
                    }
            results[name] = {
                "methods": method_signatures
            }
        except Exception as e:
            results[name] = {"error": str(e)}
            
    return results

def main():
    print("=" * 80)
    print(" GATE — QUALIFICATION TO MODELRECORD FIELD MAPPING FORENSICS")
    print("=" * 80)
    print(f"[RACINE] {PROJECT_ROOT}\n")

    res = inspect_fabric_and_qualification()

    print("[1] MÉTHODES DE LA FABRIC (core/models/fabric.py)")
    for meth, details in res.get("fabric", {}).get("methods", {}).items():
        print(f"  - {meth} : args={details['args']} -> returns={details['returns']}")

    print(f"\n[2] FONCTIONS DU BANC DE QUALIFICATION (EZZIO_Model_Qualification_Gate_v4.2.py)")
    for meth, details in res.get("qualification", {}).get("methods", {}).items():
        print(f"  - {meth} : args={details['args']} -> returns={details['returns']}")

    print("\n" + "=" * 80)
    print(" BILAN DU MAPPING ET DES SIGNATURES")
    print("================================================================================")
    print("  - Analyse statique des signatures d'interface achevée.")
    print("  - Aucune modification de code n'a été effectuée.")
    print("================================================================================")

    out_file = PROJECT_ROOT / "tools" / "qualification_mapping_report.json"
    with open(out_file, "w", encoding="utf-8") as f:
        json.dump(res, f, indent=2)
    print(f"\n[+] Rapport exporté : {out_file}")
    print("=" * 80)

if __name__ == "__main__":
    main()