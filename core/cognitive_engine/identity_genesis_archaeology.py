"""
E-ZZIO V7.59.6 — Identity Genesis Archaeology
Extrait et catégorise l'intégralité des 19 entrées identity_core
et 55 entrées experience_ledger du snapshot V7.58 pour cartographier
le modèle d'organes, de talents et de genèse cognitive.
"""

import json
import sqlite3
from pathlib import Path

ROOT_DIR = Path(r"G:\AI\E-zzio")
SNAPSHOT_DB = ROOT_DIR / "runtime" / "cognitive" / "snapshots" / "V7.58" / "memory_index.sqlite"
OUTPUT_REPORT = ROOT_DIR / "runtime" / "audit" / "system" / "identity_genesis_autopsy.json"


def run_identity_archaeology():
    if not SNAPSHOT_DB.exists():
        print(f"[!] Erreur : Base SQLite du snapshot introuvable : {SNAPSHOT_DB}")
        return

    print("[*] Extraction de la genèse identitaire depuis le snapshot V7.58...")
    uri = f"file:{SNAPSHOT_DB}?mode=ro"

    identity_entries = []
    experience_entries = []

    with sqlite3.connect(uri, uri=True) as conn:
        cursor = conn.cursor()

        # 1. Extraction des 19 identity_core
        cursor.execute("""
            SELECT rowid, content, source_path, confidence, importance, last_validated
            FROM memory_search
            WHERE memory_type = 'identity_core';
        """)
        for row in cursor.fetchall():
            identity_entries.append(
                {
                    "rowid": row[0],
                    "content": row[1],
                    "source_path": row[2],
                    "confidence": row[3],
                    "importance": row[4],
                    "last_validated": row[5],
                }
            )

        # 2. Extraction des 55 experience_ledger
        cursor.execute("""
            SELECT rowid, content, source_path, confidence, importance, last_validated
            FROM memory_search
            WHERE memory_type = 'experience_ledger';
        """)
        for row in cursor.fetchall():
            experience_entries.append(
                {
                    "rowid": row[0],
                    "content": row[1],
                    "source_path": row[2],
                    "confidence": row[3],
                    "importance": row[4],
                    "last_validated": row[5],
                }
            )

    report = {
        "snapshot_version": "V7.58",
        "identity_core_count": len(identity_entries),
        "experience_ledger_count": len(experience_entries),
        "identity_core_records": identity_entries,
        "experience_ledger_records": experience_entries,
    }

    OUTPUT_REPORT.parent.mkdir(parents=True, exist_ok=True)
    with open(OUTPUT_REPORT, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2, ensure_ascii=False)

    print("\n" + "=" * 60)
    print(" IDENTITY GENESIS AUTOPSY REPORT (V7.59.6)")
    print("=" * 60)
    print(f" Entrées 'identity_core' récupérées    : {len(identity_entries)}")
    print(f" Entrées 'experience_ledger' récupérées : {len(experience_entries)}")
    print("-" * 60)
    print(" APERÇU DES ÉLÉMENTS FONDATEURS (identity_core) :")
    for idx, e in enumerate(identity_entries[:5], 1):
        snippet = e["content"].replace("\n", " ")[:90]
        print(f"  {idx}. [{e['source_path']}] -> {snippet}...")
    print("-" * 60)
    print(" APERÇU DE LA TÉLÉMÉTRIE VÉCUE (experience_ledger) :")
    for idx, e in enumerate(experience_entries[:5], 1):
        snippet = e["content"].replace("\n", " ")[:90]
        print(f"  {idx}. [{e['source_path']}] -> {snippet}...")
    print("=" * 60)
    print(f" Rapport d'autopsie généré : {OUTPUT_REPORT}")


if __name__ == "__main__":
    run_identity_archaeology()
