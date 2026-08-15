"""
E-ZZIO V7.59.7.1 — Night Mutation Provenance (Corrected)
Analyse les fichiers du noyau et du runtime, extrait leurs dépendances Python (imports),
calcule les fenêtres de co-création temporelle (±10 min) et structure le graphe d'évolution.
"""
import os
import json
import re
from pathlib import Path
from datetime import datetime, time, timedelta, timezone

ROOT_DIR = Path(r"G:\AI\E-zzio")
TARGET_DIRS = ["core", "runtime"]
EXCLUDE_PATTERNS = [".venv", "__pycache__", "cache", "logs", ".tmp", ".bak"]
OUTPUT_REPORT = ROOT_DIR / "runtime" / "audit" / "system" / "mutation_event_graph.json"

def is_nocturnal_window(dt: datetime) -> bool:
    t = dt.time()
    return t >= time(21, 0) or t < time(3, 0)

def extract_python_imports(file_path: Path) -> list:
    imports = []
    try:
        with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
            for line in f:
                line_stripped = line.strip()
                if match := re.match(r'^(?:import|from)\s+([a-zA-Z0-9_\.]+)', line_stripped):
                    mod = match.group(1).split('.')[0]
                    if mod not in imports:
                        imports.append(mod)
    except Exception:
        pass
    return imports

def build_mutation_graph():
    print("[*] Analyse des mutations et construction du graphe d'évolution (V7.59.7.1)...")
    nodes = []

    for target in TARGET_DIRS:
        dir_path = ROOT_DIR / target
        if not dir_path.exists():
            continue

        for path in dir_path.rglob('*'):
            if path.is_file() and path.suffix.lower() == ".py":
                rel_path = path.relative_to(ROOT_DIR).as_posix()
                if any(ex in rel_path.lower() for ex in EXCLUDE_PATTERNS):
                    continue

                try:
                    stat = path.stat()
                    ctime = datetime.fromtimestamp(stat.st_ctime)
                    mtime = datetime.fromtimestamp(stat.st_mtime)

                    is_nocturnal = is_nocturnal_window(ctime) or is_nocturnal_window(mtime)
                    imports = extract_python_imports(path)

                    nodes.append({
                        "path": rel_path,
                        "filename": path.name,
                        "creation_time": ctime.isoformat(),
                        "modification_time": mtime.isoformat(),
                        "is_nocturnal": is_nocturnal,
                        "imports": imports,
                        "size_bytes": stat.st_size
                    })
                except Exception:
                    continue

    nodes.sort(key=lambda x: x["creation_time"])

    for i, node in enumerate(nodes):
        node_ctime = datetime.fromisoformat(node["creation_time"])
        co_created = []
        
        for j, other in enumerate(nodes):
            if i == j:
                continue
            other_ctime = datetime.fromisoformat(other["creation_time"])
            diff = abs((node_ctime - other_ctime).total_seconds())
            
            if diff <= 600:
                co_created.append(other["path"])

        node["co_created_window_10min"] = co_created

    graph_data = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "total_nodes": len(nodes),
        "nodes": nodes
    }

    OUTPUT_REPORT.parent.mkdir(parents=True, exist_ok=True)
    with open(OUTPUT_REPORT, "w", encoding="utf-8") as f:
        json.dump(graph_data, f, indent=2, ensure_ascii=False)

    print("\n" + "=" * 65)
    print(" MUTATION EVENT GRAPH REPORT (V7.59.7.1)")
    print("=" * 65)
    print(f" Nœuds du noyau analysés : {len(nodes)}")
    print("-" * 65)
    print(" SÉQUENCE CHRONOLOGIQUE DES MODULES (Extrait Nuit) :")
    nocturnal_count = 0
    for node in nodes:
        if node["is_nocturnal"]:
            nocturnal_count += 1
            print(f"  [NUIT] [{node['creation_time'][:19]}] {node['path']}")
            if node["co_created_window_10min"]:
                print(f"         └─ Co-créé avec : {', '.join([Path(p).name for p in node['co_created_window_10min']])}")
    print("-" * 65)
    print(f" Total modules identifiés en période nocturne : {nocturnal_count}")
    print("=" * 65)
    print(f" Rapport exporté : {OUTPUT_REPORT}")

if __name__ == "__main__":
    build_mutation_graph()
