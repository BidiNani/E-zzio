from __future__ import annotations
import json
import ast
import sys
from pathlib import Path
from typing import Dict, Any, List

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))
EXCLUDED_DIRS = {"audit", "tests", "snapshot", "snapshots", "backup", "backups", "old", "archive", ".venv", "venv", "__pycache__", ".pytest_cache", ".git", "tools"}

def inspect_fabric_qualification_methods() -> Dict[str, Any]:
    fabric_path = PROJECT_ROOT / "core" / "models" / "fabric.py"
    if not fabric_path.exists():
        return {"exists": False}
    
    try:
        content = fabric_path.read_text(encoding="utf-8", errors="replace")
        tree = ast.parse(content, filename=str(fabric_path))
        lines = content.splitlines()
        
        target_funcs = {"qualify_candidates", "activate_qualified", "qualify"}
        methods_source = {}
        
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name in target_funcs:
                start = node.lineno - 1
                end = getattr(node, 'end_lineno', start + 60)
                methods_source[node.name] = "\n".join(lines[start:end])
                
        return {
            "exists": True,
            "methods": methods_source
        }
    except Exception as e:
        return {"exists": True, "error": str(e)}

def main():
    print("=" * 80)
    print(" GATE — FABRIC QUALIFICATION & ACTIVATION FORENSICS")
    print("=" * 80)
    print(f"[RACINE] {PROJECT_ROOT}\n")

    res = inspect_fabric_qualification_methods()

    for mname, src in res.get("methods", {}).items():
        print(f"\n--- Méthode : {mname} ---\n{src}\n")

    print("\n" + "=" * 80)
    print(" BILAN DE L'INSPECTION DU PONT FABRIC QUALIFICATION")
    print("================================================================================")
    print("  - Analyse statique réalisée en lecture seule.")
    print("  - Aucune modification de code n'a été effectuée.")
    print("================================================================================")

    out_file = PROJECT_ROOT / "tools" / "fabric_qualification_mapping_report.json"
    with open(out_file, "w", encoding="utf-8") as f:
        json.dump(res, f, indent=2)
    print(f"\n[+] Rapport exporté : {out_file}")
    print("=" * 80)

if __name__ == "__main__":
    main()