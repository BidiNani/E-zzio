from __future__ import annotations
import ast
import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))
EXCLUDED = {"tools", "audit", "tests", ".venv", "venv", ".git", "__pycache__"}

def locate_ezzio_router() -> tuple[Path | None, str | None]:
    for p in PROJECT_ROOT.glob("**/*.py"):
        if set(p.parts) & EXCLUDED:
            continue
        try:
            content = p.read_text(encoding="utf-8", errors="replace")
            if "class EzzioRouter" in content:
                return p, content
        except Exception:
            continue
    return None, None

def main():
    print("=" * 80)
    print(" GATE v6.45.50 — EZZIOROUTER TERMINAL FORENSICS")
    print("=" * 80)
    print(f"[RACINE] {PROJECT_ROOT}\n")

    router_path, content = locate_ezzio_router()
    if not router_path or not content:
        print("❌ Définition 'class EzzioRouter' introuvable dans le workspace actif.")
        return

    print(f"📁 Fichier canonique trouvé : {router_path.relative_to(PROJECT_ROOT)}")
    
    try:
        tree = ast.parse(content, filename=str(router_path))
        extracted = {}
        
        for stmt in tree.body:
            if isinstance(stmt, ast.ClassDef) and stmt.name == "EzzioRouter":
                print(f"\n  🏛️  CLASS EzzioRouter (ligne {stmt.lineno})")
                for item in stmt.body:
                    if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef)):
                        extracted[item.name] = ast.unparse(item)
                        print(f"      • Méthode extraite : {item.name}()")

        print("\n[+] IMPLÉMENTATION TERMINALE DE L'EZZIOROUTER :")
        print("-" * 80)
        for name, code in extracted.items():
            print(f"\n--- [ {name} ] ---")
            print(code)
            print("-" * 40)

        out_file = PROJECT_ROOT / "tools" / "gate_v6_45_50_report.json"
        with open(out_file, "w", encoding="utf-8") as f:
            json.dump(extracted, f, indent=2)
        print(f"\n[+] Rapport d'arbitrage exporté : {out_file}")

    except Exception as e:
        print(f"❌ Erreur d'analyse AST : {e}")

    print("=" * 80)

if __name__ == "__main__":
    main()