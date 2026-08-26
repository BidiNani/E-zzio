"""
E-ZZIO V7.59.2.1 — Deep Taxonomy Validation
Inspecte de près le contenu des 62 RPG_MEMORY, traque les 8 SYNTHETIC_NOISE
et évalue un échantillon de security_audit pour certifier l'absence de faux positifs.
"""

import sys
import sqlite3
from pathlib import Path

ROOT_DIR = Path(r"G:\AI\E-zzio")
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

INDEX_DB = ROOT_DIR / "runtime" / "cognitive" / "index" / "memory_index.sqlite"

from core.cognitive_engine.taxonomy_repair import TaxonomyRepairValidator


def deep_validate():
    if not INDEX_DB.exists():
        print("[!] Base FTS5 introuvable.")
        return

    print("[*] Lancement de la validation approfondie de l'index...")
    validator = TaxonomyRepairValidator()

    uri = f"file:{INDEX_DB}?mode=ro"

    rpg_samples = []
    noise_samples = []
    security_samples_count = 0
    total_audited = 0

    with sqlite3.connect(uri, uri=True) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT source_path, content, memory_type FROM memory_search;")
        rows = cursor.fetchall()
        total_audited = len(rows)

        for source_path, content, old_type in rows:
            dummy_path = ROOT_DIR / source_path
            eval_res = validator.evaluate_source(dummy_path, content)
            m_type = eval_res["memory_type"]

            if m_type == "RPG_MEMORY":
                rpg_samples.append({"path": source_path, "snippet": content[:140]})
            elif m_type == "SYNTHETIC_NOISE":
                noise_samples.append({"path": source_path, "reason": eval_res["reason"]})
            elif m_type == "security_audit":
                security_samples_count += 1

    print("\n" + "=" * 60)
    print(" RÉSULTAT DE LA VALIDATION APPROFONDIE V7.59.2.1")
    print("=" * 60)
    print(f" Total enregistrements analysés : {total_audited}")
    print(f" Total SECURITY_AUDIT validés : {security_samples_count}")
    print(f" Total RPG_MEMORY identifiés  : {len(rpg_samples)}")
    print(f" Total SYNTHETIC_NOISE détectés: {len(noise_samples)}")
    print("-" * 60)

    print("\n[ÉCHANTILLON] Premières entrées RPG_MEMORY :")
    if rpg_samples:
        for idx, item in enumerate(rpg_samples[:5], 1):
            print(f"  {idx}. [Source: {item['path']}]")
            print(f"     Extrait: {item['snippet']}...\n")
    else:
        print("  -> Aucune entrée RPG trouvée.")

    print("\n[ÉCHANTILLON] Entrées classées SYNTHETIC_NOISE (Bruit) :")
    if noise_samples:
        for idx, item in enumerate(noise_samples, 1):
            print(f"  {idx}. [Path: {item['path']}] -> Motif: {item['reason']}")
    else:
        print("  -> Aucune entrée de bruit détectée.")
    print("=" * 60)


if __name__ == "__main__":
    deep_validate()
