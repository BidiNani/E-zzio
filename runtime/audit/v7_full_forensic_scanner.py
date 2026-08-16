import os
import sys
import json
import hashlib
import ast
import re
from pathlib import Path
from datetime import datetime
from collections import defaultdict
from concurrent.futures import ProcessPoolExecutor, as_completed

ROOT_DIR = Path("G:/AI/E-zzio").resolve()
OUTPUT_DIR = ROOT_DIR / "runtime" / "audit" / "intelligence_scan"

EXCLUDED_DIRS = {".git", "__pycache__", "venv", "node_modules", "runtime/audit", ".svelte-kit"}
TARGET_EXTENSIONS = {".py", ".json", ".jsonl", ".yaml", ".yml", ".toml", ".ini", ".ps1", ".md", ".key", ".env"}

def hash_file(file_path: Path) -> str:
    h = hashlib.sha256()
    with open(file_path, "rb") as f:
        while chunk := f.read(8192):
            h.update(chunk)
    return h.hexdigest()

def analyze_python_file(file_path: Path, rel_path: str) -> dict:
    try:
        content = file_path.read_text(encoding="utf-8", errors="replace")
        tree = ast.parse(content, filename=rel_path)
    except Exception as e:
        return {"path": rel_path, "error": f"AST_PARSE_ERROR: {str(e)}"}

    classes = []
    functions = []
    imports = []
    calls = []
    routes = []
    discord_handlers = []
    todos = []

    for i, line in enumerate(content.splitlines(), 1):
        if "TODO" in line or "FIXME" in line:
            todos.append({"line": i, "text": line.strip()})

    for node in ast.walk(tree):
        if isinstance(node, ast.ClassDef):
            classes.append(node.name)
        elif isinstance(node, ast.FunctionDef):
            functions.append(node.name)
            for dec in node.decorator_list:
                dec_str = ast.unparse(dec) if hasattr(ast, 'unparse') else ""
                if any(r in dec_str for r in ["get", "post", "put", "delete", "router"]):
                    routes.append({"function": node.name, "decorator": dec_str})
                if "event" in dec_str or "command" in dec_str:
                    discord_handlers.append({"function": node.name, "decorator": dec_str})
        elif isinstance(node, ast.Import):
            for alias in node.names:
                imports.append(alias.name)
        elif isinstance(node, ast.ImportFrom):
            if node.module:
                imports.append(f"{node.module}.{node.names[0].name}" if node.names else node.module)
        elif isinstance(node, ast.Call):
            if isinstance(node.func, ast.Name):
                calls.append(node.func.id)
            elif isinstance(node.func, ast.Attribute):
                calls.append(node.func.attr)

    return {
        "path": rel_path,
        "classes": classes,
        "functions": functions,
        "imports": list(set(imports)),
        "calls": list(set(calls)),
        "routes": routes,
        "discord_handlers": discord_handlers,
        "todos": todos,
        "line_count": len(content.splitlines())
    }

def process_file(file_path: Path) -> dict:
    rel_path = str(file_path.relative_to(ROOT_DIR)).replace("\\", "/")
    stat = file_path.stat()
    
    file_record = {
        "path": rel_path,
        "extension": file_path.suffix.lower(),
        "size_bytes": stat.st_size,
        "modified_at": datetime.fromtimestamp(stat.st_mtime).isoformat(),
        "sha256": hash_file(file_path),
        "domain": detect_domain(rel_path)
    }

    if file_path.suffix.lower() == ".py":
        file_record["py_analysis"] = analyze_python_file(file_path, rel_path)
    elif file_path.suffix.lower() in [".json", ".yaml", ".yml", ".toml"]:
        file_record["config_keys"] = inspect_config_keys(file_path)

    return file_record

def inspect_config_keys(file_path: Path) -> list:
    try:
        if file_path.suffix.lower() == ".json":
            data = json.loads(file_path.read_text(encoding="utf-8", errors="replace"))
            return list(data.keys()) if isinstance(data, dict) else ["array_root"]
    except Exception:
        return ["parse_error"]
    return []

def detect_domain(path: str) -> str:
    p = path.lower()
    if "core/" in p: return "INTELLIGENCE_CORE"
    if "memory" in p or "state/" in p: return "MEMORY_PERSISTENCE"
    if "persona" in p or "identity" in p: return "PERSONA_IDENTITY"
    if "autonomy" in p or "skills" in p: return "AUTONOMY_PLANNING"
    if "discord" in p or "interfaces/" in p: return "DISCORD_SUBSYSTEM"
    if "router" in p or "api" in p: return "API_ROUTERS"
    if "trust" in p or "security" in p or "guardian" in p or "governor" in p: return "SECURITY_TRUST"
    if "hardware" in p or "recovery" in p or "supervisor" in p: return "INFRASTRUCTURE_HARDWARE"
    if p.endswith((".json", ".yaml", ".yml", ".toml", ".env", ".ini")): return "CONFIGURATION"
    return "SUPPORT_TESTS"

def run_forensic_scan():
    print(f"[*] Initialisation du scan forensic V7 sur {ROOT_DIR}")
    files_to_process = []

    for path in ROOT_DIR.rglob("*"):
        if path.is_file() and path.suffix.lower() in TARGET_EXTENSIONS:
            rel_parts = path.relative_to(ROOT_DIR).parts
            if not any(ex in rel_parts for ex in EXCLUDED_DIRS):
                files_to_process.append(path)

    print(f"[*] {len(files_to_process)} fichiers cibles retenus. Lancement de 6 workers...")

    results = []
    with ProcessPoolExecutor(max_workers=6) as executor:
        futures = {executor.submit(process_file, fp): fp for fp in files_to_process}
        for future in as_completed(futures):
            results.append(future.result())

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    
    (OUTPUT_DIR / "inventory_forensic.json").write_text(json.dumps(results, indent=2, ensure_ascii=False), encoding="utf-8")
    
    build_dependency_graph(results)
    build_domain_reports(results)

def build_dependency_graph(results: list):
    graph = {}
    for item in results:
        if "py_analysis" in item and "imports" in item["py_analysis"]:
            path = item["path"]
            graph[path] = {
                "imports": item["py_analysis"]["imports"],
                "imported_by": []
            }

    for path, data in graph.items():
        for imp in data["imports"]:
            for target_path in graph.keys():
                mod_name = Path(target_path).stem
                if mod_name == imp or imp.replace(".", "/") in target_path:
                    graph[target_path]["imported_by"].append(path)

    (OUTPUT_DIR / "dependency_graph_forensic.json").write_text(json.dumps(graph, indent=2, ensure_ascii=False), encoding="utf-8")

def build_domain_reports(results: list):
    domain_counts = defaultdict(int)
    for item in results:
        domain_counts[item["domain"]] += 1

    report = [
        "# E-ZZIO V7 — Full Repository Forensic Report",
        f"**Date :** {datetime.now().isoformat()}",
        f"**Fichiers analysés :** {len(results)}",
        "",
        "## 1. Répartition par Domaine Fonctionnel",
    ]
    for domain, count in domain_counts.items():
        report.append(f"- **{domain}** : {count} fichiers")

    (OUTPUT_DIR / "FORENSIC_SUMMARY.md").write_text("\n".join(report), encoding="utf-8")
    print(f"[OK] Rapport forensic enregistré dans {OUTPUT_DIR}")

if __name__ == "__main__":
    run_forensic_scan()
