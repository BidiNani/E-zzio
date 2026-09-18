"""
E-ZZIO V7.59.4 — Forensic Discovery
Scan en lecture seule de tout le corpus à la recherche de marqueurs RPG,
sans se soucier des règles du Gatekeeper, pour identifier les candidats potentiels.
"""

import json
from pathlib import Path

ROOT_DIR = Path(r"G:\AI\E-zzio")
# Augmentons la sensibilité pour la phase de découverte
RPG_MARKERS = {
    "wow": 2,
    "wotlk": 3,
    "druid": 3,
    "feral": 3,
    "raid": 2,
    "boss": 2,
    "macro": 2,
    "talent": 1,
    "gear": 1,
    "loot": 1,
    "guild": 1,
    "instance": 1,
    "profession": 1,
    "capcap": 3,
    "warlock": 2,
}


def scan_corpus():
    print("[*] Scan forensique complet pour découverte RPG...")
    candidates = []

    # Extensions de données textuelles uniquement pour ce scan
    targets = {".md", ".jsonl", ".txt", ".json"}

    for path in ROOT_DIR.rglob("*"):
        if path.is_file() and path.suffix.lower() in targets:
            try:
                with open(path, encoding="utf-8", errors="ignore") as f:
                    content = f.read().lower()

                hits = {kw: weight for kw, weight in RPG_MARKERS.items() if kw in content}
                if hits:
                    score = sum(hits.values())
                    candidates.append(
                        {"path": str(path.relative_to(ROOT_DIR)), "score": score, "hits": list(hits.keys()), "snippet": content[:100]}
                    )
            except Exception:
                continue

    # Tri par score décroissant
    candidates.sort(key=lambda x: x["score"], reverse=True)

    output_path = ROOT_DIR / "runtime/audit/system/rpg_discovery_results.json"
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(candidates, f, indent=2)

    print("-" * 50)
    print(f" Découverte terminée : {len(candidates)} fichiers contiennent des marqueurs RPG.")
    print(f" Rapport sauvegardé : {output_path}")
    print("-" * 50)
    print(" Top 5 candidats découverts :")
    for c in candidates[:5]:
        print(f" [{c['score']}] {c['path']} (Hits: {', '.join(c['hits'])})")


if __name__ == "__main__":
    scan_corpus()
