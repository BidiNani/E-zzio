"""
E-ZZIO V7.59.4.4 — Snapshot DB Inspector
Vérifie la structure et la distribution exacte des types mémoriels
dans le snapshot immuable V7.58.
"""

import sqlite3
from pathlib import Path

ROOT_DIR = Path(r"G:\AI\E-zzio")
SNAPSHOT_DB = ROOT_DIR / "runtime" / "cognitive" / "snapshots" / "V7.58" / "memory_index.sqlite"


def inspect_snapshot():
    if not SNAPSHOT_DB.exists():
        print(f"[!] Erreur : Base du snapshot introuvable : {SNAPSHOT_DB}")
        return

    print("[*] Inspection forensique de la base SQLite du snapshot V7.58...")
    uri = f"file:{SNAPSHOT_DB}?mode=ro"

    with sqlite3.connect(uri, uri=True) as conn:
        cursor = conn.cursor()

        # 1. Lister les tables
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
        tables = [t[0] for t in cursor.fetchall()]
        print(f" Tables détectées dans le snapshot : {tables}")

        # 2. Inspecter la table de recherche / index
        target_table = "memory_search" if "memory_search" in tables else (tables[0] if tables else None)

        if not target_table:
            print("[!] Aucune table exploitable trouvée.")
            return

        print(f"[*] Analyse de la distribution des types dans la table '{target_table}'...")

        try:
            cursor.execute(f"SELECT memory_type, COUNT(*) FROM {target_table} GROUP BY memory_type;")
            rows = cursor.fetchall()

            print("\n" + "=" * 50)
            print(" DISTRIBUTION DES TYPES DANS LE SNAPSHOT V7.58")
            print("=" * 50)
            total = 0
            for m_type, count in rows:
                print(f"   - {str(m_type):<20} : {count} entrées")
                total += count
            print("-" * 50)
            print(f" TOTAL ENREGISTREMENTS : {total}")
            print("=" * 50)

            # Recherche spécifique des lignes contenant 'rpg' ou 'RPG' peu importe le type
            cursor.execute(
                f"SELECT source_path, memory_type FROM {target_table} WHERE memory_type LIKE '%RPG%' OR source_path LIKE '%rpg%';"
            )
            rpg_matches = cursor.fetchall()
            print(f"\n[*] Correspondances textuelles 'RPG' dans le snapshot : {len(rpg_matches)}")
            for m in rpg_matches[:5]:
                print(f"   * Type: {m[1]} | Source: {m[0]}")

        except Exception as e:
            print(f"[!] Erreur lors de l'analyse SQL : {e}")


if __name__ == "__main__":
    inspect_snapshot()
