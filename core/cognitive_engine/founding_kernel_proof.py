"""
E-ZZIO V7.59.8 — Founding Kernel Proof
Construit le DAG complet des dépendances du noyau, calcule les métriques de centralité,
identifie les nœuds racines (Roots), ponts (Bridges) et terminaux (Finals),
et exporte le manifeste mathématique `founding_kernel.json`.
"""

import hashlib
import json
import re
from datetime import UTC, datetime
from pathlib import Path

ROOT_DIR = Path(r"G:\AI\E-zzio")
TARGET_DIRS = ["core", "runtime"]
EXCLUDE_PATTERNS = [".venv", "__pycache__", "cache", "logs", ".tmp", ".bak", "tests"]
OUTPUT_REPORT = ROOT_DIR / "runtime" / "audit" / "system" / "founding_kernel.json"


def compute_sha256(file_path: Path) -> str:
    hasher = hashlib.sha256()
    try:
        with open(file_path, "rb") as f:
            while chunk := f.read(8192):
                hasher.update(chunk)
        return hasher.hexdigest()
    except Exception:
        return "ERROR"


def extract_local_imports(file_path: Path, all_modules: set) -> list:
    imports = []
    try:
        with open(file_path, encoding="utf-8", errors="ignore") as f:
            for line in f:
                line_stripped = line.strip()
                if match := re.match(r"^(?:import|from)\s+([a-zA-Z0-9_\.]+)", line_stripped):
                    mod_path = match.group(1).replace(".", "/")
                    for m in all_modules:
                        if m.startswith(mod_path) and m != file_path.relative_to(ROOT_DIR).as_posix()[:-3]:
                            if m not in imports:
                                imports.append(m)
    except Exception:
        pass
    return imports


def analyze_kernel():
    print("[*] Analyse structurelle et construction du DAG des dépendances...")

    file_map = {}
    all_modules = set()

    for target in TARGET_DIRS:
        dir_path = ROOT_DIR / target
        if not dir_path.exists():
            continue
        for path in dir_path.rglob("*"):
            if path.is_file() and path.suffix.lower() == ".py":
                rel_path = path.relative_to(ROOT_DIR).as_posix()
                if any(ex in rel_path.lower() for ex in EXCLUDE_PATTERNS):
                    continue
                file_map[rel_path] = path
                all_modules.add(rel_path[:-3])

    nodes = {}
    for rel_path, path in file_map.items():
        stat = path.stat()
        ctime = datetime.fromtimestamp(stat.st_ctime, UTC).isoformat()
        sha256 = compute_sha256(path)
        local_deps = extract_local_imports(path, all_modules)

        nodes[rel_path] = {
            "module": rel_path,
            "first_seen": ctime[:10],
            "timestamp": ctime,
            "size_bytes": stat.st_size,
            "sha256": sha256,
            "dependencies": local_deps,
            "dependents": [],
        }

    # Calcul des dépendents (in-degree / reachability)
    for _rel_path, node in nodes.items():
        for dep in node["dependencies"]:
            # Normaliser le chemin du module importé vers le rel_path si possible
            for candidate in nodes.keys():
                if candidate.startswith(dep):
                    if rel_path not in nodes[candidate]["dependents"]:
                        nodes[candidate]["dependents"].append(rel_path)

    # Calcul des métriques de centralité et de criticité
    max_deps = max((len(n["dependencies"]) + len(n["dependents"]) for n in nodes.values()), default=1)

    kernel_records = []
    for _rel_path, node in nodes.items():
        total_connections = len(node["dependencies"]) + len(node["dependents"])
        centrality = round(total_connections / max_deps, 3) if max_deps > 0 else 0.0
        descendants_count = len(node["dependents"])

        if node["first_seen"] <= "2026-06-10" and total_connections >= 3:
            criticality = "FOUNDATIONAL"
        elif total_connections >= 5:
            criticality = "BRIDGE"
        else:
            criticality = "PERIPHERAL"

        kernel_records.append(
            {
                "module": node["module"],
                "first_seen": node["first_seen"],
                "descendants": descendants_count,
                "centrality": centrality,
                "criticality": criticality,
                "hash_verified": node["sha256"] != "ERROR",
                "sha256": node["sha256"],
            }
        )

    # Tri par centralité et descendants
    kernel_records.sort(key=lambda x: (x["centrality"], x["descendants"]), reverse=True)

    roots = [n for n in kernel_records if len(nodes[n["module"]]["dependencies"]) == 0]
    bridges = [n for n in kernel_records if n["criticality"] == "BRIDGE"]
    finals = [n for n in kernel_records if len(nodes[n["module"]]["dependents"]) == 0]

    report = {
        "generated_at": datetime.now(UTC).isoformat(),
        "total_analyzed_nodes": len(kernel_records),
        "top_root_nodes": roots[:20],
        "top_bridge_nodes": bridges[:20],
        "top_final_nodes": finals[:20],
        "full_kernel_registry": kernel_records,
    }

    OUTPUT_REPORT.parent.mkdir(parents=True, exist_ok=True)
    with open(OUTPUT_REPORT, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2, ensure_ascii=False)

    print("\n" + "=" * 65)
    print(" FOUNDING KERNEL PROOF REPORT (V7.59.8)")
    print("=" * 65)
    print(f" Total nœuds cartographiés dans le DAG : {len(kernel_records)}")
    print("-" * 65)
    print(" TOP 10 NŒUDS FONDATEURS (CRITICALITY: FOUNDATIONAL / BRIDGE) :")
    for r in kernel_records[:10]:
        print(f"  - [{r['criticality']:<12}] {r['module']:<35} (Cent: {r['centrality']}, Desc: {r['descendants']})")
    print("=" * 65)
    print(f" Rapport exporté : {OUTPUT_REPORT}")


if __name__ == "__main__":
    analyze_kernel()
