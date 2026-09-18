"""
E-ZZIO V7.29.3 — Identity State Machine & Event Logger
Définit les états d'intégrité identitaire et consigne les événements système.
"""

import json
from datetime import UTC, datetime
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent.parent
EVENT_LOG_PATH = ROOT_DIR / "runtime" / "identity" / "identity_events.jsonl"


class IdentityState:
    VERIFIED = "VERIFIED"
    WARNING = "WARNING"
    COMPROMISED = "COMPROMISED"
    FAIL_CLOSED = "FAIL_CLOSED"


class IdentityEventManager:
    @staticmethod
    def log_event(event_type: str, state: str, details: dict) -> dict:
        EVENT_LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
        payload = {"timestamp": datetime.now(UTC).isoformat(), "event_type": event_type, "state": state, "details": details}
        with open(EVENT_LOG_PATH, "a", encoding="utf-8") as f:
            f.write(json.dumps(payload, ensure_ascii=False) + "\n")
        return payload
