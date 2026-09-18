"""
E-ZZIO V7.59.2 — Forensic Recall Audit (Read-Only)
1. Autopsie détaillée des 17 entrées RPG_MEMORY (chemin, contenu, score).
2. Inspection structurelle des entrées SECURITY et de leur source réelle.
3. Vérification de l'étanchéité face au bruit de laboratoire (SYNTHETIC_NOISE).
"""

import json
import sqlite3
from pathlib import Path

ROOT_DIR = Path(r"G:\AI\E-zzio")
INDEX_DB = ROOT_DIR / "runtime" / "cognitive" / "index" / "memory_index.sqlite"
FORENSIC_REPORT = ROOT_DIR / "runtime" / "audit" / "system" / "v759_forensic_recall_report.json"


def run_forensic_audit():
    if not INDEX_DB.exists():
        print("[!] Erreur : Base FTS5 introuvable.")
        return

    print("[*] Lancement de l'autopsie forensique de l'index FTS5...")

    uri = f"file:{INDEX_DB}?mode=ro"

    audit_data = {"rpg_memory_autopsy": [], "security_sample": [], "noise_inspection": [], "statistics": {}}

    with sqlite3.connect(uri, uri=True) as conn:
        cursor = conn.cursor()

        # 1. Autopsie des entrées RPG_MEMORY
        cursor.execute("""
            SELECT rowid, content, source_path, confidence, importance, memory_type
            FROM memory_search
            WHERE memory_type = 'RPG_MEMORY' OR source_path LIKE '%rpg%' OR source_path LIKE '%wow%' OR source_path LIKE '%wotlk%';
        """)
        rpg_rows = cursor.fetchall()
        for row in rpg_rows:
            audit_data["rpg_memory_autopsy"].append(
                {
                    "rowid": row[0],
                    "content_preview": row[1][:120],
                    "source_path": row[2],
                    "confidence": row[3],
                    "importance": row[4],
                    "memory_type": row[5],
                }
            )

        # 2. Échantillon des entrées SECURITY (Top 10 sources)
        cursor.execute("""
            SELECT source_path, COUNT(*), memory_type
            FROM memory_search
            WHERE memory_type = 'security_audit' OR source_path LIKE '%audit%' OR source_path LIKE '%security%'
            GROUP BY source_path
            ORDER BY COUNT(*) DESC
            LIMIT 10;
        """)
        sec_rows = cursor.fetchall()
        for row in sec_rows:
            audit_data["security_sample"].append({"source_path": row[0], "count": row[1], "memory_type": row[2]})

        # 3. Inspection des bruits résiduels potentiels (sandbox / fuzz / test)
        cursor.execute("""
            SELECT source_path, content, memory_type
            FROM memory_search
            WHERE source_path LIKE '%test%' OR source_path LIKE '%sandbox%' OR source_path LIKE '%fuzz%';
        """)
        noise_rows = cursor.fetchall()
        for row in noise_rows:
            audit_data["noise_inspection"].append({"source_path": row[0], "content_preview": row[1][:100], "memory_type": row[2]})

        # Stats globales
        cursor.execute("SELECT COUNT(*) FROM memory_search;")
        audit_data["statistics"]["total_records"] = cursor.fetchone()[0]

    # Sauvegarde du rapport forensique
    FORENSIC_REPORT.parent.mkdir(parents=True, exist_ok=True)
    with open(FORENSIC_REPORT, "w", encoding="utf-8") as f:
        json.dump(audit_data, f, ensure_ascii=False, indent=2)

    # Affichage console rigoureux
    print("\n" + "=" * 60)
    print(" RAPPORT D'AUTOPSIE FORENSIQUE FTS5 (V7.59.2)")
    print("=" * 60)
    print(f" Total enregistrements indexés : {audit_data['statistics']['total_records']}")
    print(f" Entrées RPG_MEMORY détectées : {len(audit_data['rpg_memory_autopsy'])}")
    print("-" * 60)

    print("\n[AUTOPSIE] Échantillon des entrées RPG_MEMORY :")
    if audit_data["rpg_memory_autopsy"]:
        for item in audit_data["rpg_memory_autopsy"][:5]:
            print(f"  - Source : {item['source_path']}")
            print(f"    Extrait : {item['content_preview']}...")
    else:
        print("  -> ATTENTION : Aucune entrée RPG trouvée avec ces critères.")

    print("\n[AUTOPSIE] Top Sources de la catégorie Sécurité/Audit :")
    for sec in audit_data["security_sample"][:5]:
        print(f"  - {sec['source_path']:<45} : {sec['count']} entrées ({sec['memory_type']})")

    print(f"\n[AUTOPSIE] Entrées issues de chemins de test/sandbox dans l'index : {len(audit_data['noise_inspection'])}")
    print("=" * 60)
    print(f" Rapport détaillé généré : {FORENSIC_REPORT}")


if __name__ == "__main__":
    run_forensic_audit()
