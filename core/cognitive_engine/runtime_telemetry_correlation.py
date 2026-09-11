"""
E-ZZIO V7.59.10 — Runtime Operational Telemetry & Ledger Cross-Correlation
Analyse et corrèle les journaux de décision (router_decisions.jsonl) et de sécurité
avec la fenêtre nocturne du 12 août 2026 (00:20:22 -> 03:00:00).
"""

import json
from pathlib import Path
from datetime import datetime

ROOT_DIR = Path(r"G:\AI\E-zzio")
START_TIME = datetime.fromisoformat("2026-08-12T00:20:22")
END_TIME = datetime.fromisoformat("2026-08-12T03:00:00")
OUTPUT_REPORT = ROOT_DIR / "runtime" / "audit" / "system" / "operational_telemetry_correlation.json"

LOG_TARGETS = [
    "runtime/decisions/router_decisions.jsonl",
    "runtime/audit/discord/access_granted.jsonl",
    "runtime/audit/discord/access_denied.jsonl",
    "runtime/audit/discord/security_events.jsonl",
    "runtime/audit/discord/chaos_chain.jsonl",
]


def parse_timestamp(item: dict) -> datetime:
    for key in ["timestamp", "created_at", "time", "date"]:
        if key in item:
            try:
                val = item[key]
                if isinstance(val, str):
                    return datetime.fromisoformat(val.replace("Z", "+00:00").split("+")[0])
            except Exception:
                continue
    return None


def run_correlation():
    print("[*] Lancement de la corrélation opérationnelle des journaux d'exécution...")
    correlated_events = []

    for rel_path in LOG_TARGETS:
        file_path = ROOT_DIR / rel_path
        if not file_path.exists():
            continue

        try:
            with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                for line_num, line in enumerate(f, 1):
                    line_stripped = line.strip()
                    if not line_stripped:
                        continue
                    try:
                        data = json.loads(line_stripped)
                        dt = parse_timestamp(data)
                        if dt and START_TIME <= dt <= END_TIME:
                            correlated_events.append(
                                {"source": rel_path, "line": line_num, "timestamp": dt.isoformat(), "payload_snippet": str(data)[:150]}
                            )
                    except json.JSONDecodeError:
                        continue
        except Exception:
            continue

    # Tri chronologique des événements opérationnels
    correlated_events.sort(key=lambda x: x["timestamp"])

    report = {
        "window_start": START_TIME.isoformat(),
        "window_end": END_TIME.isoformat(),
        "total_operational_events": len(correlated_events),
        "events": correlated_events,
    }

    OUTPUT_REPORT.parent.mkdir(parents=True, exist_ok=True)
    with open(OUTPUT_REPORT, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2, ensure_ascii=False)

    print("\n" + "=" * 65)
    print(" OPERATIONAL TELEMETRY CORRELATION REPORT (V7.59.10)")
    print("=" * 65)
    print(f" Événements opérationnels isolés dans la fenêtre : {len(correlated_events)}")
    print("-" * 65)
    if correlated_events:
        for ev in correlated_events[:15]:
            print(f"  [{ev['timestamp']}] ({ev['source']}) -> {ev['payload_snippet']}...")
    else:
        print("  -> Aucun événement direct dans la fenêtre dans ces fichiers spécifiques.")
    print("=" * 65)
    print(f" Rapport exporté : {OUTPUT_REPORT}")


if __name__ == "__main__":
    run_correlation()
