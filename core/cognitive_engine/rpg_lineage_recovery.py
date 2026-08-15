"""
E-ZZIO V7.59.4.3 — RPG Memory Lineage Recovery
Extrait les 17 entrées RPG_MEMORY originales du snapshot V7.58.1,
génère le manifeste cryptographique et initialise l'espace curatif 
`runtime/cognitive/curated/rpg_memory/`.
"""
import sqlite3
import json
import hashlib
from pathlib import Path
from datetime import datetime, timezone

ROOT_DIR = Path(r"G:\AI\E-zzio")
SNAPSHOT_DB = ROOT_DIR / "runtime" / "cognitive" / "snapshots" / "V7.58" / "memory_index.sqlite"
CURATED_DIR = ROOT_DIR / "runtime" / "cognitive" / "curated" / "rpg_memory"
AUDIT_REPORT = ROOT_DIR / "runtime" / "audit" / "system" / "v759_rpg_curated_lineage.json"

def recover_rpg_lineage():
    if not SNAPSHOT_DB.exists():
        print(f"[!] Erreur critique : Snapshot V7.58 introuvable à l'emplacement {SNAPSHOT_DB}")
        return

    print("[*] Récupération de la lignée RPG depuis le snapshot immuable V7.58...")

    uri = f"file:{SNAPSHOT_DB}?mode=ro"
    recovered_entries = []

    with sqlite3.connect(uri, uri=True) as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT content, source_path, confidence, importance, last_validated
            FROM memory_search
            WHERE memory_type = 'RPG_MEMORY';
        """)
        rows = cursor.fetchall()

        for content, source_path, confidence, importance, last_validated in rows:
            # Calcul du SHA-256 propre pour chaque entrée curée
            entry_bytes = content.encode("utf-8")
            entry_hash = hashlib.sha256(entry_bytes).hexdigest()

            recovered_entries.append({
                "memory_domain": "RPG_MEMORY",
                "source_path": source_path,
                "content": content,
                "confidence": confidence,
                "importance": importance,
                "last_validated": last_validated,
                "sha256": entry_hash
            })

    # Création de l'espace curatif permanent
    CURATED_DIR.mkdir(parents=True, exist_ok=True)
    
    approved_file = CURATED_DIR / "approved_entries.jsonl"
    manifest_file = CURATED_DIR / "rpg_memory_manifest.json"

    # Écriture du fichier JSONL curé
    with open(approved_file, "w", encoding="utf-8") as f:
        for entry in recovered_entries:
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")

    # Calcul du hash global du manifeste curatif
    manifest_data = {
        "domain": "RPG_MEMORY",
        "version": "V7.60",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "total_entries": len(recovered_entries),
        "entries_manifest": [{"source": e["source_path"], "sha256": e["sha256"]} for e in recovered_entries]
    }

    manifest_bytes = json.dumps(manifest_data, sort_keys=True).encode("utf-8")
    manifest_data["global_manifest_sha256"] = hashlib.sha256(manifest_bytes).hexdigest()

    with open(manifest_file, "w", encoding="utf-8") as f:
        json.dump(manifest_data, f, indent=2, ensure_ascii=False)

    # Rapport d'audit global
    AUDIT_REPORT.parent.mkdir(parents=True, exist_ok=True)
    with open(AUDIT_REPORT, "w", encoding="utf-8") as f:
        json.dump(manifest_data, f, indent=2, ensure_ascii=False)

    print("\n" + "=" * 60)
    print(" RPG MEMORY LINEAGE RECOVERY SUCCESS (V7.59.4.3)")
    print("=" * 60)
    print(f" Entrées RPG récupérées et sanctuarisées : {len(recovered_entries)}")
    print(f" Dossier curatif cible : {CURATED_DIR}")
    print(f" Manifeste cryptographique : {manifest_file.name}")
    print(f" Empreinte globale SHA256 : {manifest_data['global_manifest_sha256']}")
    print("-" * 60)
    print(" Aperçu des sources d'origine restaurées :")
    for idx, e in enumerate(recovered_entries[:5], 1):
        print(f"   {idx}. [Source: {e['source_path']}] -> Snippet: {e['content'][:70]}...")
    print("=" * 60)

if __name__ == "__main__":
    recover_rpg_lineage()
