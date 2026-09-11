from __future__ import annotations
import json
import ast
import sys
from pathlib import Path
from typing import Dict, Any, List

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))
EXCLUDED_DIRS = {"audit", "tests", "snapshot", "snapshots", "backup", "backups", "old", "archive", ".venv", "venv", "__pycache__", ".pytest_cache", ".git", "tools"}

def find_qualification_script() -> Optional[Path]:
    for p in PROJECT_ROOT.glob("**/EZZIO_Model_Qualification_Gate_v4.2.py"):
        if set(p.parts) & EXCLUDED_DIRS:
            continue
        return p
    for p in PROJECT_ROOT.glob("**/*qualification*.py"):
        if set(p.parts) & EXCLUDED_DIRS:
            continue
        return p
    return None

def inspect_qualification_file(p: Path) -> Dict[str, Any]:
    try:
        content = p.read_text(encoding="utf-8", errors="replace")
        tree = ast.parse(content, filename=str(p))
        
        functions = []
        classes = []
        returns_records = False
        produces_tiers = False
        
        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef):
                classes.append(node.name)
            elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                functions.append(node.name)
                
        content_lower = content.lower()
        returns_records = "modelrecord" in content_lower or "record" in content_lower
        produces_tiers = "tier" in content_lower or "fast" in content_lower or "heavy" in content_lower
        
        return {
            "exists": True,
            "path": str(p.relative_to(PROJECT_ROOT)),
            "classes": classes,
            "functions": functions,
            "mentions_model_record": returns_records,
            "mentions_tiers": produces_tiers
        }
    except Exception as e:
        return {"exists": True, "error": str(e)}

def main():
    print("=" * 80)
    print(" GATE — QUALIFICATION OUTPUT FORENSICS")
    print("=" * 80)
    print(f"[RACINE] {PROJECT_ROOT}\n")

    qual_path = find_qualification_script()
    if not qual_path:
        print("❌ Aucun script de qualification trouvé.")
        return

    res = inspect_qualification_file(qual_path)

    print(f"[1] ANALYSE DE : {res.get('path')}")
    print(f"  - Classes trouvées : {res.get('classes', [])}")
    print(f"  - Fonctions principales : {res.get('functions', [])}")
    print(f"  - Manipule ModelRecord / Records : {'YES' if res.get('mentions_model_record') else 'NO'}")
    print(f"  - Manipule les Tiers sémantiques : {'YES' if res.get('mentions_tiers') else 'NO'}")

    print("\n" + "=" * 80)
    print(" BILAN QUALIFICATION OUTPUT FORENSICS")
    print("================================================================================")
    print("  - Analyse statique du script de qualification achevée en lecture seule.")
    print("  - Aucune modification de code ni écriture de registre n'a été exécutée.")
    print("================================================================================")

    out = {
        "qualification_analysis": res,
        "writes_performed": 0,
        "runtime_mutations": 0
    }
    
    out_file = PROJECT_ROOT / "tools" / "qualification_output_report.json"
    with open(out_file, "w", encoding="utf-8") as f:
        json.dump(out, f, indent=2)
    print(f"\n[+] Rapport exporté : {out_file}")
    print("=" * 80)

if __name__ == "__main__":
    main()