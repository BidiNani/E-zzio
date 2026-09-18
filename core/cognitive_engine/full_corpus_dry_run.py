"""
E-ZZIO V7.59.4 — Full Corpus Dry-Run (Forensic Read-Only)
Scanne le corpus complet, applique le CognitiveGatekeeper, et produit
le rapport final de préparation à l'indexation.
"""

import json
import sys
from collections import Counter
from pathlib import Path

ROOT_DIR = Path(r"G:\AI\E-zzio")
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from core.cognitive_engine.cognitive_gatekeeper import CognitiveGatekeeper


def run_dry_run():
    gk = CognitiveGatekeeper()

    stats = {
        "total_files": 0,
        "taxonomy": Counter(),
        "indexable_count": 0,
        "quarantine_count": 0,
        "protected_identity_found": [],
        "rpg_samples": [],
    }

    print("[*] Scan complet du corpus E-zzio en cours...")

    for path in ROOT_DIR.rglob("*"):
        if path.is_file():
            stats["total_files"] += 1
            # Simulation d'évaluation
            eval_res = gk.evaluate(path)

            m_type = eval_res["memory_type"]
            stats["taxonomy"][m_type] += 1

            if eval_res["indexable"]:
                stats["indexable_count"] += 1
            else:
                stats["quarantine_count"] += 1

            # Traçage spécifique
            if eval_res.get("protected"):
                stats["protected_identity_found"].append(path.name)
            if m_type == "RPG_MEMORY":
                if len(stats["rpg_samples"]) < 10:
                    stats["rpg_samples"].append(str(path))

    print("\n" + "=" * 60)
    print(" RAPPORT FINAL FULL CORPUS DRY-RUN (V7.59.4)")
    print("=" * 60)
    print(f" 1. Fichiers scannés au total     : {stats['total_files']}")
    print(f" 2. Indexables (Hippocampe)       : {stats['indexable_count']}")
    print(f" 3. Non-Indexables (Quarantine)   : {stats['quarantine_count']}")
    print("-" * 60)
    print(" RÉPARTITION COGNITIVE :")
    for m_type, count in stats["taxonomy"].items():
        print(f"   - {m_type:<20} : {count}")
    print("-" * 60)
    print(f" 4. Identité (19 attendus)        : {len(stats['protected_identity_found'])}")
    print(f" 5. RPG Mémoire (Rappel)          : {stats['taxonomy'].get('RPG_MEMORY', 0)}")
    print("=" * 60)

    if len(stats["protected_identity_found"]) < 19:
        print("[!] ALERTE : Identité incomplète. Vérifier le Registre.")

    # Génération du rapport
    with open(ROOT_DIR / "runtime/audit/system/full_corpus_dry_run.json", "w") as f:
        json.dump(stats, f, indent=2)


if __name__ == "__main__":
    run_dry_run()
