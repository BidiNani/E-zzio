from __future__ import annotations
import json
import ast
import sys
from pathlib import Path
from typing import Dict, Any, List

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))
EXCLUDED_DIRS = {"audit", "tests", "snapshot", "snapshots", "backup", "backups", "old", "archive", ".venv", "venv", "__pycache__", ".pytest_cache", ".git", "tools"}

def inspect_model_record_definition() -> Dict[str, Any]:
    record_fields = []
    consumers = []
    
    target_files = [
        "core/models/registry.py",
        "core/models/lifecycle.py",
        "core/models/fabric.py",
        "core/cognition/cognitive_router.py"
    ]
    
    details = {}
    
    for f in target_files:
        p = PROJECT_ROOT / f
        if not p.exists():
            continue
        try:
            content = p.read_text(encoding="utf-8", errors="replace")
            tree = ast.parse(content, filename=str(p))
            
            classes = []
            fields = []
            for node in ast.walk(tree):
                if isinstance(node, ast.ClassDef):
                    classes.append(node.name)
                    if "Record" in node.name or "Model" in node.name:
                        for subnode in ast.walk(node):
                            if isinstance(subnode, ast.AnnAssign) and isinstance(subnode.target, ast.Name):
                                fields.append(subnode.target.id)
            details[f] = {
                "classes": classes,
                "fields_detected": fields
            }
        except Exception as e:
            details[f] = {"error": str(e)}
            
    return details

def main():
    print("=" * 80)
    print(" GATE — MODEL RECORD CONTRACT FORENSICS")
    print("=" * 80)
    print(f"[RACINE] {PROJECT_ROOT}\n")

    report = inspect_model_record_definition()

    for path, info in report.items():
        print(f"[FICHIER] {path}")
        print(f"  - Classes : {info.get('classes', [])}")
        print(f"  - Champs détectés : {info.get('fields_detected', [])}")
        print("")

    print("--------------------------------------------------------------------------------")
    print(" [VERDICT]")
    print(" - Structure de ModelRecord et des classes associées cartographiée.")
    print("================================================================================")

    out_file = PROJECT_ROOT / "tools" / "model_record_contract_report.json"
    with open(out_file, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2)
    print(f"\n[+] Rapport exporté : {out_file}")
    print("=" * 80)

if __name__ == "__main__":
    main()