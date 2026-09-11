from __future__ import annotations
import json
import ast
import sys
from pathlib import Path
from typing import Dict, Any, List

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))
EXCLUDED_DIRS = {"audit", "tests", "snapshot", "snapshots", "backup", "backups", "old", "archive", ".venv", "venv", "__pycache__", ".pytest_cache", ".git", "tools"}

def extract_function_body(file_path: Path, func_names: List[str]) -> Dict[str, str]:
    if not file_path.exists():
        return {}
    
    try:
        content = file_path.read_text(encoding="utf-8", errors="replace")
        tree = ast.parse(content, filename=str(file_path))
        
        extracted = {}
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                if node.name in func_names:
                    # Extraire le code source de la fonction
                    lines = content.splitlines()
                    start_line = node.lineno - 1
                    end_line = node.end_lineno if hasattr(node, 'end_lineno') else start_line + 20
                    func_source = "\n".join(lines[start_line:end_line])
                    extracted[node.name] = func_source
        return extracted
    except Exception as e:
        return {"error": str(e)}

def main():
    print("=" * 80)
    print(" GATE — FABRIC AND QUALIFICATION BODY FORENSICS")
    print("=" * 80)
    print(f"[RACINE] {PROJECT_ROOT}\n")

    fabric_path = PROJECT_ROOT / "core" / "models" / "fabric.py"
    qual_path = PROJECT_ROOT / "EZZIO_Model_Qualification_Gate_v4.2.py"

    fabric_funcs = extract_function_body(fabric_path, ["qualify_candidates", "activate_qualified", "_sync_router_with_registry", "discover"])
    qual_funcs = extract_function_body(qual_path, ["run_model"])

    print("[1] CORPS EXTRAITS DE AutonomousModelFabric (core/models/fabric.py)")
    for name, src in fabric_funcs.items():
        print(f"\n--- Fonction : {name} ---\n{src[:600]}...\n[... tronqué si trop long ...]")

    print("\n[2] CORPS EXTRAIT DE run_model (EZZIO_Model_Qualification_Gate_v4.2.py)")
    for name, src in qual_funcs.items():
        print(f"\n--- Fonction : {name} ---\n{src[:600]}...\n[... tronqué si trop long ...]")

    print("\n" + "=" * 80)
    print(" BILAN DE L'EXTRACTION DES CORPS")
    print("================================================================================")
    print("  - Analyse des implémentations internes achevée en lecture seule.")
    print("  - Aucune modification de code n'a été effectuée.")
    print("================================================================================")

    out = {
        "fabric_bodies": {k: len(v) for k, v in fabric_funcs.items()},
        "qualification_bodies": {k: len(v) for k, v in qual_funcs.items()},
        "writes_performed": 0,
        "runtime_mutations": 0
    }
    
    out_file = PROJECT_ROOT / "tools" / "body_extraction_report.json"
    with open(out_file, "w", encoding="utf-8") as f:
        json.dump(out, f, indent=2)
    print(f"\n[+] Rapport exporté : {out_file}")
    print("=" * 80)

if __name__ == "__main__":
    main()