import json
from pathlib import Path
from collections import defaultdict

ROOT_DIR = Path("G:/AI/E-zzio").resolve()
SCAN_DIR = ROOT_DIR / "runtime" / "audit" / "intelligence_scan"

def analyze_forensic_data():
    inventory_file = SCAN_DIR / "inventory_forensic.json"
    graph_file = SCAN_DIR / "dependency_graph_forensic.json"

    if not inventory_file.exists() or not graph_file.exists():
        print(f"[ERROR] Fichiers de rapport introuvables dans {SCAN_DIR}")
        return

    print("[*] Chargement des données d'audit forensic...")
    inventory = json.loads(inventory_file.read_text(encoding="utf-8"))
    dep_graph = json.loads(graph_file.read_text(encoding="utf-8"))

    print(f"[OK] {len(inventory)} fichiers dans l'inventaire.")

    # 1. Détection des doublons stricts par SHA256
    hash_map = defaultdict(list)
    for item in inventory:
        hash_map[item["sha256"]].append(item["path"])

    sha_duplicates = {h: paths for h, paths in hash_map.items() if len(paths) > 1}

    # 2. Détection des fichiers Python orphelins
    entry_points_keywords = ["master", "server", "bot", "main", "cli", "script", "test", "guardian"]
    orphans = []
    
    for path, data in dep_graph.items():
        imported_by = data.get("imported_by", [])
        if len(imported_by) == 0:
            filename = Path(path).name.lower()
            if not any(k in filename or k in path.lower() for k in entry_points_keywords):
                orphans.append(path)

    # 3. Cartographie des chaînes d'exécution à partir des points d'entrée majeurs
    entry_targets = [
        "core/ezzio_master.py",
        "web_server.py",
        "core/pc_commander.py",
        "core/dispatcher.py"
    ]
    
    execution_chains = {}
    for target in entry_targets:
        if target in dep_graph:
            execution_chains[target] = {
                "direct_imports": dep_graph[target].get("imports", []),
                "imported_by_count": len(dep_graph[target].get("imported_by", []))
            }

    # 4. Génération du rapport de synthèse Markdown
    generate_analysis_markdown(inventory, sha_duplicates, orphans, execution_chains)

def generate_analysis_markdown(inventory, sha_duplicates, orphans, execution_chains):
    output_md = SCAN_DIR / "V7_FORENSIC_ANALYSIS.md"
    
    lines = [
        "# E-ZZIO V7 — Rapport d'Analyse Structurelle Forensic",
        f"**Fichiers analysés :** {len(inventory)}",
        "",
        "## 1. Integrité & Doublons Stricts (Identiques par SHA256)",
        f"**Nombre de groupes de fichiers 100% identiques :** {len(sha_duplicates)}",
        ""
    ]

    for h, paths in list(sha_duplicates.items())[:10]:
        lines.append(f"- Hash `{h[:12]}...` ({len(paths)} copies) :")
        for p in paths:
            lines.append(f"  - `{p}`")

    lines.extend([
        "",
        "## 2. Modules Python Potentiellement Orphelins",
        f"**Nombre de modules sans dépendants entrants (hors scripts/entrypoints) :** {len(orphans)}",
        ""
    ])

    for o in orphans[:15]:
        lines.append(f"- `{o}`")

    lines.extend([
        "",
        "## 3. Chaînes d'Exécution des Points d'Entrée Principaux",
        ""
    ])

    for target, info in execution_chains.items():
        lines.append(f"### Point d'Entrée : `{target}`")
        lines.append(f"- **Importé par :** {info['imported_by_count']} module(s)")
        lines.append(f"- **Imports directs ({len(info['direct_imports'])}) :**")
        for imp in info["direct_imports"][:10]:
            lines.append(f"  - `{imp}`")
        lines.append("")

    output_md.write_text("\n".join(lines), encoding="utf-8")
    print(f"[OK] Rapport d'analyse forensic enregistré dans {output_md}")

if __name__ == "__main__":
    analyze_forensic_data()
