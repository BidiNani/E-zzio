from __future__ import annotations
import ast
import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

def find_ezzio_router_file() -> Path | None:
    for p in PROJECT_ROOT.glob("**/*.py"):
        if any(exc in p.parts for exc in {".venv", "venv", ".git", "__pycache__", "audit", "tests", "snapshots", "backup", "tools"}):
            continue
        try:
            content = p.read_text(encoding="utf-8", errors="replace")
            if "class EzzioRouter" in content or "class Router" in content:
                if "model_list" in content or "set_model_list" in content or "execute" in content:
                    return p
        except Exception:
            continue
    return None

def main():
    print("=" * 80)
    print(" GATE v6.45.49 — CORRIGÉ (EXCLUSION TOOLS)")
    print("=" * 80)
    
    router_path = find_ezzio_router_file()
    if not router_path or not router_path.exists():
        print("❌ Fichier EzzioRouter introuvable dans le workspace actif (hors tools).")
        return

    print(f"📁 Fichiers source du routeur détecté : {router_path.relative_to(PROJECT_ROOT)}")
    
    try:
        content = router_path.read_text(encoding="utf-8", errors="replace")
        tree = ast.parse(content, filename=str(router_path))
        
        extracted_methods = {}
        for stmt in tree.body:
            if isinstance(stmt, ast.ClassDef) and ("Router" in stmt.name):
                print(f"\n  🏛️  CLASS {stmt.name} (ligne {stmt.lineno})")
                for item in stmt.body:
                    if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef)):
                        if item.name in {"__init__", "set_model_list", "execute", "route", "select_model"}:
                            extracted_methods[item.name] = ast.unparse(item)
                            print(f"      • Extraction méthode : {item.name}()")

        print("\n[+] ANALYSE DU CODE SOURCE :")
        print("-" * 80)
        for name, code in extracted_methods.items():
            print(f"\n--- [ {name} ] ---")
            print(code)
            print("-" * 40)

        out_file = PROJECT_ROOT / "tools" / "gate_v6_45_49_report.json"
        with open(out_file, "w", encoding="utf-8") as f:
            json.dump(extracted_methods, f, indent=2)

    except Exception as e:
        print(f"❌ Erreur : {e}")

    print("=" * 80)

if __name__ == "__main__":
    main()