import os
import sys
import json
import ast
from pathlib import Path

ROOT_PATH = Path(r"G:\AI\E-zzio")
AUDIT_DIR = ROOT_PATH / "runtime" / "audit" / "reliability"
AUDIT_DIR.mkdir(parents=True, exist_ok=True)

EXCLUDED_DIRS = {".venv", ".git", "__pycache__", "node_modules", "archive", "logs", "audit"}

# 1. Standard Library
STDLIB_MODULES = (
    set(sys.stdlib_module_names)
    if hasattr(sys, "stdlib_module_names")
    else {
        "os",
        "sys",
        "json",
        "re",
        "time",
        "pathlib",
        "logging",
        "asyncio",
        "subprocess",
        "urllib",
        "typing",
        "contextlib",
        "dataclasses",
        "enum",
        "math",
        "hashlib",
        "hmac",
        "concurrent",
    }
)

# 2. Dépendances PIP externes déclarées
EXTERNAL_LIBS = {
    "uvicorn",
    "fastapi",
    "pydantic",
    "psutil",
    "requests",
    "aiohttp",
    "jinja2",
    "dotenv",
    "google",
    "discord",
    "cpuinfo",
    "flask",
    "PIL",
    "openai",
    "mss",
    "pytest",
    "blake3",
    "cryptography",
    "yaml",
    "httpx",
    "starlette",
}


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


def resolve_module_path(mod_name, file_path, file_map):
    rel_py = mod_name.replace(".", "/") + ".py"
    rel_init = mod_name.replace(".", "/") + "/__init__.py"

    # Vérification depuis la racine du projet
    if rel_py.lower() in file_map or rel_init.lower() in file_map:
        return True

    # Vérification relative au dossier du fichier source
    parent_rel = file_path.parent.relative_to(ROOT_PATH).as_posix().lower()
    local_py = f"{parent_rel}/{rel_py}".lower()
    local_init = f"{parent_rel}/{rel_init}".lower()
    if local_py in file_map or local_init in file_map:
        return True

    # Vérification dans core/ et runtime/
    for prefix in ["core", "runtime", "scripts"]:
        pref_py = f"{prefix}/{rel_py}".lower()
        pref_init = f"{prefix}/{rel_init}".lower()
        if pref_py in file_map or pref_init in file_map:
            return True

    return False


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

            resolved = resolve_module_path(mod_name, file_path, file_map)

            item = {"source": rel_src, "reference": mod_name, "resolved": resolved}
            deps.append(item)
            if not resolved:
                broken.append(item)

    return deps, broken


def run_audit():
    print("[*] Démarrage de l'audit AST v3.0 (PIP Externe + Imports Relatifs)...")
    file_map = get_all_files()
    all_deps, all_broken = [], []

    for rel_path, full_path in file_map.items():
        if full_path.suffix.lower() == ".py":
            deps, broken = audit_python_imports(full_path, file_map)
            all_deps.extend(deps)
            all_broken.extend(broken)

    (AUDIT_DIR / "dependency_graph_v3.json").write_text(json.dumps(all_deps, indent=2), encoding="utf-8")
    (AUDIT_DIR / "broken_references_v3.json").write_text(json.dumps(all_broken, indent=2), encoding="utf-8")

    print("\n=== SYNTHÈSE DE FIABILITÉ AST V3 ===")
    print(f"Fichiers de code scannés    : {len(file_map)}")
    print(f"Imports internes analysés   : {len(all_deps)}")
    print(f"Références brisées réelles  : {len(all_broken)}")
    print(f"[OK] Rapports générés dans  : {AUDIT_DIR}")


if __name__ == "__main__":
    run_audit()
