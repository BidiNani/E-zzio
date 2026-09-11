from __future__ import annotations
import json
import ast
import sys
from pathlib import Path
from typing import Dict, Any, List

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))
EXCLUDED_DIRS = {"audit", "tests", "snapshot", "snapshots", "backup", "backups", "old", "archive", ".venv", "venv", "__pycache__", ".pytest_cache", ".git", "tools"}

def inspect_semantic_contracts() -> Dict[str, Any]:
    registry_path = PROJECT_ROOT / "core" / "models" / "registry.py"
    if not registry_path.exists():
        return {"exists": False}
    
    try:
        content = registry_path.read_text(encoding="utf-8", errors="replace")
        tree = ast.parse(content, filename=str(registry_path))
        
        enums = {}
        init_signature = None
        
        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef):
                if node.name in {"ModelTier", "ModelLifecycle"}:
                    enum_values = []
                    for sub in node.body:
                        if isinstance(sub, ast.Assign):
                            for target in sub.targets:
                                if isinstance(target, ast.Name):
                                    enum_values.append(target.id)
                        elif isinstance(sub, ast.AnnAssign) and isinstance(sub.target, ast.Name):
                            enum_values.append(sub.target.id)
                    enums[node.name] = enum_values
                elif node.name == "ModelRecord":
                    for sub in node.body:
                        if isinstance(sub, (ast.FunctionDef, ast.AsyncFunctionDef)) and sub.name == "__init__":
                            args = [arg.arg for arg in sub.args.args]
                            init_signature = args
                            
        return {
            "exists": True,
            "enums": enums,
            "model_record_init_args": init_signature
        }
    except Exception as e:
        return {"exists": True, "error": str(e)}

def main():
    print("=" * 80)
    print(" GATE — MODEL RECORD SEMANTIC CONTRACT FORENSICS")
    print("=" * 80)
    print(f"[RACINE] {PROJECT_ROOT}\n")

    res = inspect_semantic_contracts()

    print("[1] VALEURS SÉMANTIQUES (ENUMS DANS core/models/registry.py)")
    for enum_name, values in res.get("enums", {}).items():
        print(f"  - {enum_name} : {values}")

    print(f"\n[2] SIGNATURE D'INITIALISATION DE ModelRecord")
    print(f"  - Arguments __init__ : {res.get('model_record_init_args', 'Non trouvé')}")

    print("\n" + "=" * 80)
    print(" BILAN DU CONTRAT SÉMANTIQUE")
    print("================================================================================")
    print("  - Analyse statique des enums et du constructeur ModelRecord complétée.")
    print("  - Aucune modification de code n'a été effectuée.")
    print("================================================================================")

    out_file = PROJECT_ROOT / "tools" / "model_record_semantic_report.json"
    with open(out_file, "w", encoding="utf-8") as f:
        json.dump(res, f, indent=2)
    print(f"\n[+] Rapport exporté : {out_file}")
    print("=" * 80)

if __name__ == "__main__":
    main()