"""
E-ZZIO V7.59.5.1 — Temporal Memory Archaeology
Détecte toutes les injections, créations de mémoire et événements de gouvernance
exécutés entre 01:00 et 03:00 ou portant des marqueurs de bootstrap/injection.
"""

import json
import re
from pathlib import Path

ROOT_DIR = Path(r"G:\AI\E-zzio")
TARGET_DIRS = ["state", "runtime/decisions", "registry/telemetry", "bridge", "runtime/evolution", "runtime/memory"]
OUTPUT_REPORT = ROOT_DIR / "runtime" / "audit" / "system" / "temporal_archaeology_report.json"

EVENT_KEYWORDS = ["inject", "seed", "bootstrap", "import", "memory_created", "promoted", "genesis"]


def run_temporal_archaeology():
    print("[*] Lancement du balayage temporel et événementiel (02:00 & Injections)...")
    timeline_events = []

    for target in TARGET_DIRS:
        dir_path = ROOT_DIR / target
        if not dir_path.exists():
            continue

        for path in dir_path.rglob("*"):
            if path.is_file() and path.suffix.lower() in {".jsonl", ".json", ".txt", ".log"}:
                try:
                    with open(path, "r", encoding="utf-8", errors="ignore") as f:
                        lines = f.readlines()

                    for line_num, line in enumerate(lines, 1):
                        line_lower = line.lower()

                        # Filtre 1 : Horodatage autour de 02:00 (formats ISO ou standards: T01:, T02:, T03: ou 01:, 02:, 03:)
                        has_night_timestamp = bool(re.search(r"(?:t| )0[123]:\d{2}:\d{2}", line_lower))

                        # Filtre 2 : Événement d'injection / bootstrap
                        has_injection_keyword = any(kw in line_lower for kw in EVENT_KEYWORDS)

                        if has_night_timestamp or has_injection_keyword:
                            snippet = line.strip()
                            if len(snippet) > 200:
                                snippet = snippet[:200] + "..."

                            timeline_events.append(
                                {
                                    "source_path": str(path.relative_to(ROOT_DIR)),
                                    "line_number": line_num,
                                    "matched_night_time": has_night_timestamp,
                                    "matched_injection": has_injection_keyword,
                                    "snippet": snippet,
                                }
                            )
                except Exception:
                    continue

    timeline_events.sort(key=lambda x: (x["matched_night_time"], x["matched_injection"]), reverse=True)

    report = {
        "scan_timestamp": "2026-08-12",
        "total_events_found": len(timeline_events),
        "events": timeline_events[:50],  # Rétention des 50 faits marquants
    }

    OUTPUT_REPORT.parent.mkdir(parents=True, exist_ok=True)
    with open(OUTPUT_REPORT, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2, ensure_ascii=False)

    print("\n" + "=" * 60)
    print(" TEMPORAL MEMORY ARCHAEOLOGY REPORT (V7.59.5.1)")
    print("=" * 60)
    print(f" Événements nocturnes/injections isolés : {len(timeline_events)}")
    print("-" * 60)
    if timeline_events:
        for ev in timeline_events[:10]:
            flag = "[02H]" if ev["matched_night_time"] else "[INJECT]"
            print(f" {flag} {ev['source_path']}:{ev['line_number']}")
            print(f"      {ev['snippet']}\n")
    else:
        print(" -> Aucun événement temporel ou d'injection isolé dans ces registres.")
    print("=" * 60)
    print(f" Rapport exporté : {OUTPUT_REPORT}")


if __name__ == "__main__":
    run_temporal_archaeology()
