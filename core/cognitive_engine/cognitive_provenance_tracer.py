"""
E-ZZIO V7.59 — Cognitive Provenance Tracer
Analyse la base FTS5 existante et classe chaque enregistrement selon la taxonomie à 6 niveaux :
1. IDENTITY (identity_core)
2. RPG_MEMORY (génèse et contexte utilisateur/projet)
3. EXPERIENCE (experience_ledger)
4. SECURITY (security_audit)
5. OPERATIONAL (télémétrie, bridge, system)
6. SYNTHETIC_NOISE (tests, sandbox, fuzz)
"""

import json
import sqlite3
from pathlib import Path

ROOT_DIR = Path(r"G:\AI\E-zzio")
INDEX_DB = ROOT_DIR / "runtime" / "cognitive" / "index" / "memory_index.sqlite"
PROVENANCE_REPORT = ROOT_DIR / "runtime" / "audit" / "system" / "cognitive_provenance_matrix.json"


def classify_record(source_path: str, content: str, current_memory_type: str) -> str:
    path_lower = source_path.lower()
    content_lower = content.lower()

    # 1. IDENTITY (Socle immuable / Registry / Constitution)
    if (
        "registry/core" in path_lower
        or "registry/personality" in path_lower
        or "constitution" in path_lower
        or current_memory_type == "identity_core"
    ):
        return "IDENTITY"

    # 2. RPG_MEMORY (Genèse, contexte personnel, lore, intentions)
    rpg_markers = ["rpg", "wow", "wotlk", "druid", "capcap", "identity forge", "lore", "intentions", "persona"]
    if any(m in path_lower or m in content_lower for m in rpg_markers):
        return "RPG_MEMORY"

    # 3. EXPERIENCE (Ledgers de décision et d'action réels)
    if "ledger" in path_lower or "decision" in path_lower or current_memory_type == "experience_ledger":
        return "EXPERIENCE"

    # 4. SECURITY (Audit de sécurité, accès, authentification)
    if "security" in path_lower or "audit" in path_lower or current_memory_type == "security_audit":
        return "SECURITY"

    # 5. OPERATIONAL (Bridge, state, télémétrie, config)
    if "bridge" in path_lower or "state" in path_lower or "telemetry" in path_lower or "config" in path_lower:
        return "OPERATIONAL"

    # 6. SYNTHETIC_NOISE (Tests, isolation, fuzz, benchmarks)
    noise_markers = ["test", "sandbox", "fuzz", "chaos", "soak", "benchmark", "mock"]
    if any(m in path_lower for m in noise_markers):
        return "SYNTHETIC_NOISE"

    return "OPERATIONAL"  # Par défaut si non classé


def run_tracer():
    if not INDEX_DB.exists():
        print("[!] Erreur : Base FTS5 introuvable.")
        return

    print("[*] Analyse de la provenance et classification cognitive des entrées...")

    uri = f"file:{INDEX_DB}?mode=ro"
    taxonomy_counts = {"IDENTITY": 0, "RPG_MEMORY": 0, "EXPERIENCE": 0, "SECURITY": 0, "OPERATIONAL": 0, "SYNTHETIC_NOISE": 0}
    source_mapping = {}

    with sqlite3.connect(uri, uri=True) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT source_path, content, memory_type FROM memory_search;")
        rows = cursor.fetchall()

        for source_path, content, memory_type in rows:
            tier = classify_record(source_path, content, memory_type)
            taxonomy_counts[tier] += 1

            if source_path not in source_mapping:
                source_mapping[source_path] = {"tier": tier, "count": 0}
            source_mapping[source_path]["count"] += 1

    report = {"total_records_audited": len(rows), "taxonomy_breakdown": taxonomy_counts, "source_mapping": source_mapping}

    PROVENANCE_REPORT.parent.mkdir(parents=True, exist_ok=True)
    with open(PROVENANCE_REPORT, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)

    # Affichage console synthétique
    print("-" * 50)
    print(" MATRICE DE PROVENANCE ET TAXONOMIE COGNITIVE")
    print("-" * 50)
    print(f" Total enregistrements analysés : {len(rows)}")
    print("-" * 50)
    print(" RÉPARTITION PAR NIVEAU COGNITIF :")
    for tier, count in taxonomy_counts.items():
        pct = (count / len(rows)) * 100 if len(rows) > 0 else 0
        print(f"   - {tier:<18} : {count:>5} entrées ({pct:>5.1f}%)")
    print("-" * 50)
    print(f" Rapport de matrice généré : {PROVENANCE_REPORT}")


if __name__ == "__main__":
    run_tracer()
