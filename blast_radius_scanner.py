import ast
from pathlib import Path

def scan_target(root: Path, target_class: str, target_module: str):
    found = []
    for f in root.rglob("*.py"):
        # Ignorer les dossiers virtuels et caches
        if ".venv" in f.parts or "__pycache__" in f.parts:
            continue
            
        try:
            tree = ast.parse(f.read_text(encoding="utf-8", errors="replace"))
            for node in ast.walk(tree):
                # Cherche l'instanciation de la classe
                if isinstance(node, ast.Call):
                    if isinstance(node.func, ast.Name) and node.func.id == target_class:
                        found.append(f"  [INSTANCIATION] {f.relative_to(root)} (ligne {node.lineno})")
                # Cherche l'import du module
                if isinstance(node, ast.ImportFrom):
                    if node.module and target_module in node.module:
                        found.append(f"  [IMPORT] {f.relative_to(root)} (ligne {node.lineno})")
        except Exception:
            pass
    return found

if __name__ == "__main__":
    root = Path("G:/AI/E-zzio")
    
    print("\n" + "="*80)
    print(" 🔍 ANALYSE D'IMPACT (BLAST RADIUS)")
    print("="*80)
    
    targets = [
        ("CloudGuard", "cloud_guard"),
        ("GoogleBridge", "google_bridge") # Ajuste le nom de la classe si ce n'est pas GoogleBridge
    ]
    
    for cls_name, mod_name in targets:
        print(f"\n>> Recherche des dépendances vers : {cls_name} / {mod_name}.py")
        results = scan_target(root, cls_name, mod_name)
        if results:
            for r in results:
                print(r)
        else:
            print("  Aucune dépendance trouvée (Module totalement isolé).")
            
    print("\n" + "="*80)
