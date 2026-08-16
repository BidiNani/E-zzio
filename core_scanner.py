import ast
import json
import sys
import time
from pathlib import Path

STDLIB = {"abc", "argparse", "asyncio", "collections", "concurrent", "contextlib", "copy", "dataclasses", "datetime", "enum", "functools", "hashlib", "inspect", "io", "itertools", "json", "logging", "math", "os", "pathlib", "re", "shutil", "sqlite3", "struct", "subprocess", "sys", "threading", "time", "traceback", "typing", "uuid", "warnings", "wave"}

def get_imports(file_path):
    try:
        content = file_path.read_text(encoding="utf-8")
        tree = ast.parse(content, filename=str(file_path))
    except Exception as e:
        return {"error": str(e)}

    imports = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                imports.add(alias.name.split(".")[0])
        elif isinstance(node, ast.ImportFrom):
            if node.module:
                imports.add(node.module.split(".")[0])
    return sorted(list(imports))

def categorize_import(module_name):
    if module_name in STDLIB:
        return "STDLIB"
    elif module_name in ["runtime", "core", "bootstrap", "contracts"]:
        return "INTERNAL"
    else:
        return "THIRD_PARTY"

root_dir = Path("G:/AI/E-zzio")
core_dirs = [
    root_dir / "runtime" / "core",
    root_dir / "core",
    root_dir / "runtime" / "memory",
    root_dir / "runtime" / "execution",
    root_dir / "runtime" / "agents"
]

matrix = {}
total_files = 0

for directory in core_dirs:
    if not directory.exists():
        continue
    for py_file in directory.rglob("*.py"):
        if py_file.name == "__init__.py" and py_file.stat().st_size == 0:
            continue
        imports = get_imports(py_file)
        if isinstance(imports, dict) and "error" in imports:
            continue
        rel_path = py_file.relative_to(root_dir).as_posix()
        for imp in imports:
            cat = categorize_import(imp)
            if imp not in matrix:
                matrix[imp] = {"category": cat, "used_by": []}
            matrix[imp]["used_by"].append(rel_path)
        total_files += 1

sorted_matrix = dict(sorted(matrix.items(), key=lambda item: (item[1]["category"], item[0])))

report = {
    "timestamp_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
    "files_scanned": total_files,
    "dependency_matrix": sorted_matrix
}

report_dir = root_dir / "runtime" / "tests" / "reports"
report_dir.mkdir(parents=True, exist_ok=True)
report_path = report_dir / "core_dependency_matrix.json"
report_path.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")

print("\n" + "="*80)
print(f" MATRICE DES DEPENDANCES DU NOYAU (Fichiers scannes : {total_files})")
print("="*80)

for cat in ["INTERNAL", "THIRD_PARTY"]:
    print(f"\n[{cat} DEPENDENCIES]")
    for mod, data in sorted_matrix.items():
        if data["category"] == cat:
            usages = len(data["used_by"])
            print(f"  {mod:<25} | Utilise par {usages} fichier(s)")
            for f in data["used_by"][:3]:
                print(f"    - {f}")
            if usages > 3:
                print(f"    - ... (+ {usages - 3} autres)")

print("\n" + "="*80)
print(f"Rapport JSON complet : {report_path}")
print("="*80)
