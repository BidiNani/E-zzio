from __future__ import annotations
import ast
import sys
from pathlib import Path
from typing import Dict, Any, List

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))
EXCLUDED_DIRS = {"audit", "tests", "snapshot", "snapshots", "backup", "backups", "old", "archive", ".venv", "venv", "__pycache__", ".pytest_cache", ".git", "tools"}

def inspect_file_signatures(rel_path: str, target_functions: list[str]) -> Dict[str, Any]:
    p = PROJECT_ROOT / rel_path
    if not p.exists():
        return {"exists": False}
    
    try:
        content = p.read_text(encoding="utf-8", errors="replace")
        tree = ast.parse(content, filename=str(p))
        
        signatures = {}
        docstrings = {}
        
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                if node.name in target_functions:
                    args = [arg.arg for arg in node.args.args]
                    returns = ast.unparse(node.returns) if node.returns else "None"
                    signatures[node.name] = {
                        "args": args,
                        "returns": returns
                    }
                    docstrings[node.name] = ast.get_docstring(node)
                    
        return {
            "exists": True,
            "signatures": signatures,
            "docstrings": docstrings
        }
    except Exception as e:
        return {"exists": True, "error": str(e)}

def main():
    print("=" * 80)
    print(" GATE — CONTRACT DATA-SHAPE FORENSICS")
    print("=" * 80)
    print(f"[RACINE] {PROJECT_ROOT}\n")

    gemini_audit = inspect_file_signatures("core/models/discovery/gemini.py", ["discover", "_version_rank"])
    ollama_audit = inspect_file_signatures("runtime/models/ollama_sync.py", ["fetch_ollama_models", "run_reconciliation"])
    lifecycle_audit = inspect_file_signatures("core/models/lifecycle.py", ["ingest_discovery", "fingerprint"])
    registry_audit = inspect_file_signatures("core/models/registry.py", ["upsert", "save"])

    print("[1] CONTRAT DE SORTIE : GeminiDiscovery.discover()")
    print(f"  - Signature : {gemini_audit.get('signatures', {}).get('discover', 'Non trouvée')}")
    print(f"  - Docstring : {gemini_audit.get('docstrings', {}).get('discover', 'Aucune')}")

    print(f"\n[2] CONTRAT DE SORTIE : OllamaSync (runtime/models/ollama_sync.py)")
    print(f"  - fetch_ollama_models : {ollama_audit.get('signatures', {}).get('fetch_ollama_models', 'Non trouvée')}")
    print(f"  - run_reconciliation  : {ollama_audit.get('signatures', {}).get('run_reconciliation', 'Non trouvée')}")

    print(f"\n[3] CONTRAT D'ENTRÉE : ModelLifecycleManager.ingest_discovery()")
    print(f"  - ingest_discovery    : {lifecycle_audit.get('signatures', {}).get('ingest_discovery', 'Non trouvée')}")

    print(f"\n[4] CONTRAT DE PERSISTANCE : ModelRegistry")
    print(f"  - upsert / save       : {registry_audit.get('signatures', {})}")

    print("\n" + "=" * 80)
    print(" BILAN DES FORMES DE DONNÉES (DATA-SHAPES)")
    print("================================================================================")
    print("  - Analyse structurelle des signatures et des types d'entrée/sortie achevée.")
    print("  - Aucune modification de code n'a été effectuée.")
    print("================================================================================")

    out = {
        "gemini_audit": gemini_audit,
        "ollama_audit": ollama_audit,
        "lifecycle_audit": lifecycle_audit,
        "registry_audit": registry_audit,
        "writes_performed": 0,
        "runtime_mutations": 0
    }
    
    out_file = PROJECT_ROOT / "tools" / "contract_data_shape_report.json"
    with open(out_file, "w", encoding="utf-8") as f:
        json.dump(out, f, indent=2)
    print(f"\n[+] Rapport exporté : {out_file}")
    print("=" * 80)

if __name__ == "__main__":
    main()