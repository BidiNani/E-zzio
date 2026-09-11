from __future__ import annotations
import json
import ast
import sys
from pathlib import Path
from typing import Dict, Any, List

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))
EXCLUDED_DIRS = {"audit", "tests", "snapshot", "snapshots", "backup", "backups", "old", "archive", ".venv", "venv", "__pycache__", ".pytest_cache", ".git", "tools"}

def inspect_file_wiring(rel_path: str) -> Dict[str, Any]:
    p = PROJECT_ROOT / rel_path
    if not p.exists():
        return {"exists": False}
    
    try:
        content = p.read_text(encoding="utf-8", errors="replace")
        tree = ast.parse(content, filename=str(p))
        
        classes = []
        functions = []
        calls = []
        
        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef):
                classes.append(node.name)
            elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                functions.append(node.name)
            elif isinstance(node, ast.Call):
                if isinstance(node.func, ast.Name):
                    calls.append(node.func.id)
                elif isinstance(node.func, ast.Attribute):
                    calls.append(node.func.attr)
                    
        return {
            "exists": True,
            "classes": classes,
            "functions": functions,
            "calls": list(set(calls)),
            "mentions_ingest": "ingest_discovery" in content,
            "mentions_registry": "registry" in content.lower()
        }
    except Exception as e:
        return {"exists": True, "error": str(e)}

def find_callers_of(target_name: str) -> List[str]:
    callers = []
    for p in PROJECT_ROOT.glob("**/*.py"):
        if set(p.parts) & EXCLUDED_DIRS:
            continue
        try:
            content = p.read_text(encoding="utf-8", errors="replace")
            if target_name in content:
                callers.append(str(p.relative_to(PROJECT_ROOT)))
        except Exception:
            continue
    return callers

def main():
    print("=" * 80)
    print(" GATE — DISCOVERY WIRING FORENSICS (gemini.py & ollama_sync.py)")
    print("=" * 80)
    print(f"[RACINE] {PROJECT_ROOT}\n")

    gemini_path = "core/models/discovery/gemini.py"
    sync_path = "runtime/models/ollama_sync.py"

    gemini_info = inspect_file_wiring(gemini_path)
    sync_info = inspect_file_wiring(sync_path)

    gemini_callers = find_callers_of("GeminiDiscovery") if gemini_path else []
    sync_callers = find_callers_of("OllamaSync") if sync_path else []
    if not sync_callers:
        sync_callers = find_callers_of("ollama_sync")

    print(f"[1] ANALYSE DE : {gemini_path}")
    print(f"  - Existe : {gemini_info.get('exists')}")
    print(f"  - Classes : {gemini_info.get('classes', [])}")
    print(f"  - Fonctions : {gemini_info.get('functions', [])}")
    print(f"  - Mentionne 'ingest_discovery' : {'YES' if gemini_info.get('mentions_ingest') else 'NO'}")
    print(f"  - Appelés par (fichiers) : {gemini_callers}")

    print(f"\n[2] ANALYSE DE : {sync_path}")
    print(f"  - Existe : {sync_info.get('exists')}")
    print(f"  - Classes : {sync_info.get('classes', [])}")
    print(f"  - Fonctions : {sync_info.get('functions', [])}")
    print(f"  - Mentionne 'ingest_discovery' : {'YES' if sync_info.get('mentions_ingest') else 'NO'}")
    print(f"  - Appelés par (fichiers) : {sync_callers}")

    print("\n" + "=" * 80)
    print(" BILAN DE CÂBLAGE DES PRODUCERS")
    print("================================================================================")
    print("  - Analyse structurelle et des appelants effectuée sans aucune mutation.")
    print("================================================================================")

    out = {
        "gemini_discovery": gemini_info,
        "gemini_callers": gemini_callers,
        "ollama_sync": sync_info,
        "ollama_callers": sync_callers,
        "writes_performed": 0,
        "runtime_mutations": 0
    }
    
    out_file = PROJECT_ROOT / "tools" / "discovery_wiring_report.json"
    with open(out_file, "w", encoding="utf-8") as f:
        json.dump(out, f, indent=2)
    print(f"\n[+] Rapport exporté : {out_file}")
    print("=" * 80)

if __name__ == "__main__":
    main()