import json
from datetime import datetime
from pathlib import Path

TELEMETRY_DIR = Path("G:/AI/E-zzio/registry/telemetry")
EVENTS_PATH = TELEMETRY_DIR / "events.jsonl"


def log_event(event_type, payload=None):
    TELEMETRY_DIR.mkdir(parents=True, exist_ok=True)

    entry = {
        "timestamp": datetime.now().isoformat(),
        "type": str(event_type),
        "payload": payload or {},
    }

    with EVENTS_PATH.open("a", encoding="utf-8") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")

    return entry


def read_events(limit=100):
    if not EVENTS_PATH.exists():
        return []

    lines = EVENTS_PATH.read_text(encoding="utf-8", errors="ignore").splitlines()
    items = []

    for line in lines[-limit:]:
        try:
            items.append(json.loads(line))
        except Exception:
            pass

    return items
