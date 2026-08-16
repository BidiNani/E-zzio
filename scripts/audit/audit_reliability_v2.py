import os
import sys
import json
import ast
from pathlib import Path

ROOT_PATH = Path(r"G:\AI\E-zzio")
AUDIT_DIR = ROOT_PATH / "runtime" / "audit" / "reliability"
AUDIT_DIR.mkdir(parents=True, exist_ok=True)

EXCLUDED_DIRS = {".venv", ".git", "__pycache__", "node_modules", "archive", "logs", "audit"}

# Bibliothèque standard + dépendances PIP externes principales
STDLIB_MODULES = set(sys.stdlib_module_names) if hasattr(sys, 'stdlib_module_names') else {
    "os", "sys", "json", "re", "time", "pathlib", "logging", "asyncio", "subprocess", 
    "urllib", "typing", "contextlib", "dataclasses", "enum", "math", "hashlib", "hmac", "concurrent"
}
EXTERNAL_LIBS = {"uvicorn", "fastapi", "pydantic", "psutil", "requests", "aiohttp", "jinja2"}

def get_all_files():
    file_map = {}
    for root, dirs, filenames in os.walk(ROOT_PATH):
        dirs[:] = [d for d in dirs if d not in EXCLUDED_DIRS]
        for f in filenames:
            if f.endswith((".py", ".ps1", ".json")):
                full = Path(root) / f
                rel = full.relative_to(ROOT_PATH).as_posix().lower()
                file_map[rel] = full
    return file_map

def audit_python_imports(file_path, file_map):
    deps, broken = [], []
    rel_src = file_path.relative_to(ROOT_PATH).as_posix()
    
    try:
        content = file_path.read_text(encoding="utf-8", errors="ignore")
        tree = ast.parse(content, filename=str(file_path))
    except Exception:
        return deps, broken

    for node in ast.walk(tree):
        mod_names = []
        if isinstance(node, ast.Import):
            for alias in node.names:
                mod_names.append(alias.name)
        elif isinstance(node, ast.ImportFrom):
            if node.module:
                mod_names.append(node.module)

        for mod_name in mod_names:
            base_mod = mod_name.split(".")[0]
            if base_mod in STDLIB_MODULES or base_mod in EXTERNAL_LIBS:
                continue

            # Résolution du chemin local (.py ou /__init__.py)
            mod_path_py = mod_name.replace(".", "/") + ".py"
            mod_path_init = mod_name.replace(".", "/") + "/__init__.py"

            resolved = (mod_path_py.lower() in file_map) or (mod_path_init.lower() in file_map)

            item = {"source": rel_src, "reference": mod_name, "resolved": resolved}
            deps.append(item)
            if not resolved:
                broken.append(item)

    return deps, broken

def run_audit():
    print("[*] Démarrage de l'audit de fiabilité AST (code applicatif strict)...")
    file_map = get_all_files()
    all_deps, all_broken = [], []

    for rel_path, full_path in file_map.items():
        if full_path.suffix.lower() == ".py":
            deps, broken = audit_python_imports(full_path, file_map)
            all_deps.extend(deps)
            all_broken.extend(broken)

    # Écriture des rapports qualifiés
    (AUDIT_DIR / "dependency_graph_v2.json").write_text(json.dumps(all_deps, indent=2), encoding="utf-8")
    (AUDIT_DIR / "broken_references_v2.json").write_text(json.dumps(all_broken, indent=2), encoding="utf-8")

    print("\n=== SYNTHÈSE DE FIABILITÉ AST (PROPRE) ===")
    print(f"Fichiers applicatifs scannés : {len(file_map)}")
    print(f"Imports internes analysés   : {len(all_deps)}")
    print(f"Références brisées réelles  : {len(all_broken)}")
    print(f"[OK] Rapports générés dans  : {AUDIT_DIR}")

if __name__ == "__main__":
    run_audit()
