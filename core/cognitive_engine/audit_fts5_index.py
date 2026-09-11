"""
E-ZZIO V7.59.1 — Semantic & Structural Audit of memory_index.sqlite
Analyse en lecture seule : répartition par memory_type, détection des faibles confiances
et identification des doublons de contenu/hash.
"""

import sqlite3
from pathlib import Path
import json

ROOT_DIR = Path(r"G:\AI\E-zzio")
INDEX_DB = ROOT_DIR / "runtime" / "cognitive" / "index" / "memory_index.sqlite"
AUDIT_REPORT = ROOT_DIR / "runtime" / "audit" / "system" / "fts5_semantic_audit.json"


def run_semantic_audit():
    if not INDEX_DB.exists():
        print(f"[!] Erreur : Base FTS5 introuvable à l'emplacement {INDEX_DB}")
        return

    print("[*] Analyse sémantique de l'index FTS5 en cours...")

    uri = f"file:{INDEX_DB}?mode=ro"
    with sqlite3.connect(uri, uri=True) as conn:
        cursor = conn.cursor()

        # 1. Total des enregistrements
        cursor.execute("SELECT COUNT(*) FROM memory_search;")
        total_records = cursor.fetchone()[0]

        # 2. Répartition par memory_type
        cursor.execute("""
            SELECT memory_type, COUNT(*)
            FROM memory_search
            GROUP BY memory_type
            ORDER BY COUNT(*) DESC;
        """)
        type_breakdown = {row[0]: row[1] for row in cursor.fetchall()}

        # 3. Comptage des faibles confiances (< 0.8)
        cursor.execute("SELECT COUNT(*) FROM memory_search WHERE confidence < 0.8;")
        low_confidence_count = cursor.fetchone()[0]

        # 4. Analyse des doublons par contenu exact (ou hash similaire)
        cursor.execute("""
            SELECT content, COUNT(*) as cnt
            FROM memory_search
            GROUP BY content
            HAVING cnt > 1
            ORDER BY cnt DESC
            LIMIT 10;
        """)
        top_content_duplicates = [{"content": row[0][:80], "occurrences": row[1]} for row in cursor.fetchall()]

        # 5. Répartition par source_path (Top 10)
        cursor.execute("""
            SELECT source_path, COUNT(*) as cnt
            FROM memory_search
            GROUP BY source_path
            ORDER BY cnt DESC
            LIMIT 10;
        """)
        top_sources = {row[0]: row[1] for row in cursor.fetchall()}

    audit_data = {
        "total_records": total_records,
        "memory_type_breakdown": type_breakdown,
        "low_confidence_count": low_confidence_count,
        "top_content_duplicates": top_content_duplicates,
        "top_sources": top_sources,
    }

    AUDIT_REPORT.parent.mkdir(parents=True, exist_ok=True)
    with open(AUDIT_REPORT, "w", encoding="utf-8") as f:
        json.dump(audit_data, f, ensure_ascii=False, indent=2)

    # Affichage console
    print("-" * 50)
    print(" RÉSULTAT DE L'AUDIT SÉMANTIQUE FTS5")
    print("-" * 50)
    print(f" Total enregistrements analysés : {total_records}")
    print(f" Entrées à faible confiance (<0.8): {low_confidence_count}")
    print("-" * 50)
    print(" RÉPARTITION PAR TYPE DE MÉMOIRE :")
    for m_type, count in type_breakdown.items():
        print(f"   - {m_type:<20} : {count}")
    print("-" * 50)
    print(" TOP SOURCES DANS L'INDEX :")
    for src, count in top_sources.items():
        print(f"   - {src:<40} : {count} entrées")
    print("-" * 50)
    if top_content_duplicates:
        print(f" Doublons textuels stricts détectés : {len(top_content_duplicates)} motifs majeurs")
    else:
        print(" Aucun doublon textuel strict majeur détecté.")
    print("-" * 50)
    print(f" Rapport d'audit généré : {AUDIT_REPORT}")


if __name__ == "__main__":
    run_semantic_audit()
