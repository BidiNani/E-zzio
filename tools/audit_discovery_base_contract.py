from __future__ import annotations
import json
import ast
import sys
from pathlib import Path
from typing import Dict, Any, List

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))
EXCLUDED_DIRS = {"audit", "tests", "snapshot", "snapshots", "backup", "backups", "old", "archive", ".venv", "venv", "__pycache__", ".pytest_cache", ".git", "tools"}

def inspect_ollama_discovery_contract() -> Dict[str, Any]:
    disc_base = PROJECT_ROOT / "core" / "models" / "discovery" / "base.py"
    if not disc_base.exists():
        return {"exists": False}
    
    try:
        content = disc_base.read_text(encoding="utf-8", errors="replace")
        tree = ast.parse(content, filename=str(disc_base))
        lines = content.splitlines()
        
        methods = {}
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                start = node.lineno - 1
                end = getattr(node, 'end_lineno', start + 25)
                methods[node.name] = "\n".join(lines[start:end])
                
        return {
            "exists": True,
            "base_discovery_source": methods
        }
    except Exception as e:
        return {"exists": True, "error": str(e)}

def main():
    print("=" * 80)
    print(" GATE — DISCOVERY CONTRACT FOUNDATION (PHASE 2)")
    print("=" * 80)
    print(f"[RACINE] {PROJECT_ROOT}\n")

    res = inspect_ollama_discovery_contract()

    for mname, src in res.get("base_discovery_source", {}).items():
        print(f"--- Méthode de base : {mname} ---\n{src}\n")

    print("=" * 80)
    print(" BILAN DE L'INSPECTION DU CONTRAT DE DÉCOUVERTE")
    print("================================================================================")
    print("  - Analyse statique réalisée en lecture seule.")
    print("  - Aucune modification de code n'a été effectuée.")
    print("================================================================================")

    out_file = PROJECT_ROOT / "tools" / "discovery_base_contract_report.json"
    with open(out_file, "w", encoding="utf-8") as f:
        json.dump(res, f, indent=2)
    print(f"\n[+] Rapport exporté : {out_file}")
    print("=" * 80)

if __name__ == "__main__":
    main()