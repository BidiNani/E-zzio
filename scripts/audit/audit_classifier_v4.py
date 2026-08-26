import os
import sys
import json
import ast
from pathlib import Path

ROOT_PATH = Path(r"G:\AI\E-zzio")
AUDIT_DIR = ROOT_PATH / "runtime" / "audit" / "reliability"
AUDIT_DIR.mkdir(parents=True, exist_ok=True)

# Exclusion stricte uniquement des zones mortes et de sortie d'audit
EXCLUDED_DIRS = {".venv", ".git", "__pycache__", "node_modules", "archive", "logs", "reliability", "quarantine", "guardian"}

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

    if rel_py.lower() in file_map or rel_init.lower() in file_map:
        return True

    parent_rel = file_path.parent.relative_to(ROOT_PATH).as_posix().lower()
    local_py = f"{parent_rel}/{rel_py}".lower()
    local_init = f"{parent_rel}/{rel_init}".lower()
    if local_py in file_map or local_init in file_map:
        return True

    for prefix in ["core", "runtime", "scripts"]:
        pref_py = f"{prefix}/{rel_py}".lower()
        pref_init = f"{prefix}/{rel_init}".lower()
        if pref_py in file_map or pref_init in file_map:
            return True

    return False


def categorize_source(source_path):
    src_lower = source_path.lower()
    if "quarantine" in src_lower or "archive" in src_lower:
        return "QUARANTINE_REFERENCE"
    elif "guardian" in src_lower or "experiments" in src_lower or "test_" in Path(source_path).name.lower():
        return "LEGACY_TEST_REFERENCE"
    else:
        return "REAL_RUNTIME_FAILURE"


def run_classification():
    print("[*] Lancement du classificateur AST v4.1 (Correction périmètre audit)...")
    file_map = get_all_files()
    classified_items = []

    for rel_path, full_path in file_map.items():
        if full_path.suffix.lower() != ".py":
            continue

        try:
            content = full_path.read_text(encoding="utf-8", errors="ignore")
            tree = ast.parse(content, filename=str(full_path))
        except Exception:
            continue

        rel_src = full_path.relative_to(ROOT_PATH).as_posix()

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

                if not resolve_module_path(mod_name, full_path, file_map):
                    category = categorize_source(rel_src)
                    classified_items.append({"source": rel_src, "reference": mod_name, "category": category})

    report_path = AUDIT_DIR / "classification_v4.json"
    report_path.write_text(json.dumps(classified_items, indent=2), encoding="utf-8")

    counts = {"REAL_RUNTIME_FAILURE": 0, "LEGACY_TEST_REFERENCE": 0, "QUARANTINE_REFERENCE": 0}
    for item in classified_items:
        counts[item["category"]] += 1

    print("\n=== BILAN DE CLASSIFICATION AST V4.1 ===")
    print(f"Total références non résolues : {len(classified_items)}")
    print(f"  [CRITIQUE] REAL_RUNTIME_FAILURE : {counts['REAL_RUNTIME_FAILURE']}")
    print(f"  [HERITAGE] LEGACY_TEST_REFERENCE : {counts['LEGACY_TEST_REFERENCE']}")
    print(f"  [INERTE]   QUARANTINE_REFERENCE  : {counts['QUARANTINE_REFERENCE']}")
    print(f"\n[OK] Classification détaillée exportée dans : {report_path}")


if __name__ == "__main__":
    run_classification()
