"""
E-ZZIO V7.59.7 — Identity Genesis Graph
Calcule l'horodatage, le hachage cryptographique et le graphe de références croisées
des 19 artefacts identitaires pour reconstituer la chronologie exacte de la forge d'E-ZZIO.
"""

import hashlib
import json
from datetime import UTC, datetime
from pathlib import Path

ROOT_DIR = Path(r"G:\AI\E-zzio")
OUTPUT_REPORT = ROOT_DIR / "runtime" / "audit" / "system" / "identity_genesis_graph.json"

IDENTITY_FILES = [
    "E-ZZIO — IDENTITY FORGE QUESTIONNAI.txt",
    "E-zzio_Cartographie_Self_Awareness.md",
    "persona.full.md",
    "config/constitution.json",
    "config/intentions.md",
    "config/lore.md",
    "config/persona.json",
    "registry/persona.txt",
    "registry/core/constitution.md",
    "registry/core/decision_policy.md",
    "registry/core/limitations.md",
    "registry/core/priorities.md",
    "registry/core/reasoning.md",
    "registry/core/uncertainty.md",
    "registry/core/values.md",
    "registry/personality/identity.md",
    "registry/personality/lore.md",
    "registry/personality/speech.md",
    "registry/personality/traits.md",
]


def compute_sha256(file_path: Path) -> str:
    hasher = hashlib.sha256()
    with open(file_path, "rb") as f:
        while chunk := f.read(8192):
            hasher.update(chunk)
    return hasher.hexdigest()


def build_genesis_graph():
    print("[*] Reconstitution du graphe généalogique d'identité...")
    nodes = []

    # 1. Analyse individuelle des artefacts
    for rel_path in IDENTITY_FILES:
        full_path = ROOT_DIR / rel_path
        if not full_path.exists():
            continue

        stat = full_path.stat()
        sha256 = compute_sha256(full_path)

        with open(full_path, encoding="utf-8", errors="ignore") as f:
            content = f.read()

        # Recherche de références vers les autres fichiers de l'identité
        references = []
        for other_rel in IDENTITY_FILES:
            if other_rel != rel_path:
                other_name = Path(other_rel).name.lower()
                if other_name in content.lower():
                    references.append(other_rel)

        nodes.append(
            {
                "relative_path": rel_path,
                "filename": full_path.name,
                "sha256": sha256,
                "size_bytes": stat.st_size,
                "timestamps": {
                    "created": datetime.fromtimestamp(stat.st_ctime, UTC).isoformat(),
                    "modified": datetime.fromtimestamp(stat.st_mtime, UTC).isoformat(),
                },
                "outgoing_references": references,
            }
        )

    # 2. Tri chronologique par date de création / modification
    nodes.sort(key=lambda x: x["timestamps"]["modified"])

    graph_data = {"generated_at": datetime.now(UTC).isoformat(), "total_nodes": len(nodes), "chronological_lineage": nodes}

    OUTPUT_REPORT.parent.mkdir(parents=True, exist_ok=True)
    with open(OUTPUT_REPORT, "w", encoding="utf-8") as f:
        json.dump(graph_data, f, indent=2, ensure_ascii=False)

    print("\n" + "=" * 65)
    print(" IDENTITY GENESIS GRAPH REPORT (V7.59.7)")
    print("=" * 65)
    print(f" Artefacts identitaires cartographiés : {len(nodes)}/19")
    print("-" * 65)
    print(" LIGNÉE CHRONOLOGIQUE DES ARTEFACTS (Ordre de Forge) :")
    for idx, node in enumerate(nodes, 1):
        mtime = node["timestamps"]["modified"][:19].replace("T", " ")
        refs_count = len(node["outgoing_references"])
        print(f"  {idx:02d}. [{mtime}] {node['relative_path']:<42} (Refs: {refs_count})")
    print("=" * 65)
    print(f" Rapport exporté : {OUTPUT_REPORT}")


if __name__ == "__main__":
    build_genesis_graph()
