from __future__ import annotations
import json
import ast
import sys
from pathlib import Path
from typing import Dict, Any, List

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))
EXCLUDED_DIRS = {"audit", "tests", "snapshot", "snapshots", "backup", "backups", "old", "archive", ".venv", "venv", "__pycache__", ".pytest_cache", ".git", "tools"}

def inspect_discovery_adapters() -> Dict[str, Any]:
    disc_dir = PROJECT_ROOT / "core" / "models" / "discovery"
    if not disc_dir.exists():
        return {"exists": False}
        
    results = {}
    for p in disc_dir.glob("*.py"):
        if p.name == "__init__":
            continue
        rel_path = str(p.relative_to(PROJECT_ROOT))
        try:
            content = p.read_text(encoding="utf-8", errors="replace")
            tree = ast.parse(content, filename=str(p))
            lines = content.splitlines()
            
            funcs = {}
            for node in ast.walk(tree):
                if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    start = node.lineno - 1
                    end = getattr(node, 'end_lineno', start + 35)
                    funcs[node.name] = "\n".join(lines[start:end])
                    
            results[rel_path] = funcs
        except Exception as e:
            results[rel_path] = {"error": str(e)}
            
    return results

def main():
    print("=" * 80)
    print(" GATE — DISCOVERY ADAPTERS FORENSICS")
    print("=" * 80)
    print(f"[RACINE] {PROJECT_ROOT}\n")

    res = inspect_discovery_adapters()

    for path, funcs in res.items():
        print(f"[MODULE] {path}")
        for fname, src in funcs.items():
            print(f"\n--- Fonction : {fname} ---\n{src}\n")

    print("=" * 80)
    print(" BILAN DE L'INSPECTION DES ADAPTATEURS DE DÉCOUVERTE")
    print("================================================================================")
    print("  - Analyse statique réalisée en lecture seule.")
    print("  - Aucune modification de code n'a été effectuée.")
    print("================================================================================")

    out_file = PROJECT_ROOT / "tools" / "discovery_adapters_inspection_report.json"
    with open(out_file, "w", encoding="utf-8") as f:
        json.dump(res, f, indent=2)
    print(f"\n[+] Rapport exporté : {out_file}")
    print("=" * 80)

if __name__ == "__main__":
    main()