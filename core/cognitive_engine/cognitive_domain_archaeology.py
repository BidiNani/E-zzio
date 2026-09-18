"""
E-ZZIO V7.59.5 — Cognitive Domain Archaeology
Scanne les espaces conversationnels et d'état (human_chat, human_loop, bridge)
à la recherche de signaux convergents de gaming/contexte personnel,
soumis à une validation humaine obligatoire.
"""

import json
from pathlib import Path

ROOT_DIR = Path(r"G:\AI\E-zzio")
TARGET_SCAN_DIRS = ["state/human_chat", "state/human_loop", "bridge/brain", "registry/personality"]
OUTPUT_REPORT = ROOT_DIR / "runtime" / "audit" / "system" / "cognitive_domain_candidates.json"

# Signaux thématiques nécessitant une convergence stricte (au moins 2 domaines requis)
DOMAIN_AXES = {
    "game_universe": ["wow", "wotlk", "lich king", "3.3.5", "3.3.5a"],
    "character_class": ["druid", "feral", "warlock", "priest", "mage", "paladin"],
    "activity_context": ["raid", "icc", "naxx", "ulduar", "macro", "talent", "gear", "loot"],
}


def run_domain_archaeology():
    print("[*] Lancement de l'archéologie des domaines latents...")
    candidates = []

    for target in TARGET_SCAN_DIRS:
        dir_path = ROOT_DIR / target
        if not dir_path.exists():
            continue

        for path in dir_path.rglob("*"):
            if path.is_file() and path.suffix.lower() in {".jsonl", ".json", ".md", ".txt"}:
                try:
                    with open(path, encoding="utf-8", errors="ignore") as f:
                        content = f.read().lower()

                    matched_axes = {}
                    for axis, keywords in DOMAIN_AXES.items():
                        found = [kw for kw in keywords if kw in content]
                        if found:
                            matched_axes[axis] = found

                    # Exigence de convergence : au moins 2 axes thématiques différents touchés
                    if len(matched_axes) >= 2:
                        candidates.append(
                            {
                                "source_path": str(path.relative_to(ROOT_DIR)),
                                "matched_axes": matched_axes,
                                "convergence_score": sum(len(v) for v in matched_axes.values()),
                                "promotion_status": "manual_review_required",
                            }
                        )
                except Exception:
                    continue

    report = {"scan_timestamp": "2026-08-12", "total_domain_candidates": len(candidates), "candidates": candidates}

    OUTPUT_REPORT.parent.mkdir(parents=True, exist_ok=True)
    with open(OUTPUT_REPORT, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2, ensure_ascii=False)

    print("\n" + "=" * 60)
    print(" COGNITIVE DOMAIN ARCHAEOLOGY REPORT (V7.59.5)")
    print("=" * 60)
    print(f" Candidats à fort signal de domaine : {len(candidates)}")
    print("-" * 60)
    if candidates:
        for c in candidates:
            axes_str = ", ".join(c["matched_axes"].keys())
            print(f" -> Source : {c['source_path']}")
            print(f"    Axes convergents : [{axes_str}] (Score: {c['convergence_score']})")
    else:
        print(" -> Aucun cluster de domaine latent détecté dans les zones cibles.")
    print("=" * 60)
    print(f" Rapport exporté : {OUTPUT_REPORT}")


if __name__ == "__main__":
    run_domain_archaeology()
