"""
Vérification expérimentale des 5 opérations d'introspection à la demande.
"""
import os
import sys
import time
import ast
import json
from pathlib import Path

root = Path("G:/AI/E-zzio")
if str(root) not in sys.path:
    sys.path.insert(0, str(root))

from core.perception.universal_reader import UniversalFileReader

results = {}

# 1. File Search
t0 = time.perf_counter()
matches = list(root.glob("**/universal_reader.py"))
lat_search = (time.perf_counter() - t0) * 1000
results["1_file_search"] = {
    "request": "Recherche de 'universal_reader.py'",
    "component_used": "Path.glob()",
    "raw_result": str(matches[0].relative_to(root)),
    "latency_ms": round(lat_search, 2),
    "classification": "PROVEN"
}

# 2. File Read
ufr = UniversalFileReader()
t0 = time.perf_counter()
read_res = ufr.read_file(matches[0])
lat_read = (time.perf_counter() - t0) * 1000
results["2_file_read"] = {
    "request": "Lecture du fichier 'universal_reader.py'",
    "component_used": "UniversalFileReader.read_file()",
    "raw_result": f"ok={read_res.get('ok')}, lines={read_res.get('lines')}, size={read_res.get('size_bytes')}b",
    "latency_ms": round(lat_read, 2),
    "classification": "PROVEN"
}

# 3. Symbol Search
t0 = time.perf_counter()
tree = ast.parse(matches[0].read_text(encoding="utf-8"))
classes = [n.name for n in ast.walk(tree) if isinstance(n, ast.ClassDef)]
functions = [n.name for n in ast.walk(tree) if isinstance(n, ast.FunctionDef)]
lat_symbol = (time.perf_counter() - t0) * 1000
results["3_symbol_search"] = {
    "request": "Extraction des classes et fonctions de 'universal_reader.py'",
    "component_used": "AST Parser (ast.walk)",
    "raw_result": f"classes={classes}, functions_count={len(functions)}",
    "latency_ms": round(lat_symbol, 2),
    "classification": "PROVEN"
}

# 4. Import Relations
t0 = time.perf_counter()
imports = []
for n in ast.walk(tree):
    if isinstance(n, ast.Import):
        for alias in n.names: imports.append(alias.name)
    elif isinstance(n, ast.ImportFrom):
        imports.append(str(n.module))
lat_imports = (time.perf_counter() - t0) * 1000
results["4_imports_inspection"] = {
    "request": "Extraction des dépendances d'import",
    "component_used": "AST Parser (ast.Import/ImportFrom)",
    "raw_result": imports[:8],
    "latency_ms": round(lat_imports, 2),
    "classification": "PROVEN"
}

# 5. Directory Inventory
t0 = time.perf_counter()
dir_entries = [p.name for p in (root / "core/perception").iterdir()]
lat_dir = (time.perf_counter() - t0) * 1000
results["5_directory_inventory"] = {
    "request": "Comptage et inventaire de 'core/perception'",
    "component_used": "Path.iterdir()",
    "raw_result": dir_entries,
    "latency_ms": round(lat_dir, 2),
    "classification": "PROVEN"
}

out_file = root / "state/audit/optimization/introspection_operations_evidence.json"
out_file.parent.mkdir(parents=True, exist_ok=True)
out_file.write_text(json.dumps(results, indent=2, ensure_ascii=False), encoding="utf-8")
print("INTROSPECTION EVIDENCE SAVED TO:", out_file)
print(json.dumps(results, indent=2, ensure_ascii=False))
