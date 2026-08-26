"""
E-ZZIO V7.45 — Immutable Audit Ledger (Hash Chaining)
Garantit l'intégrité infalsifiable des journaux d'événements par liaison cryptographique (Blockchain-lite).
"""

import json
import hashlib
from pathlib import Path
from datetime import datetime, timezone


class ImmutableAuditLedger:
    def __init__(self, log_path: Path):
        self.log_path = log_path
        self.log_path.parent.mkdir(parents=True, exist_ok=True)

    def _get_last_hash(self) -> str:
        if not self.log_path.exists():
            return "0" * 64
        lines = [l.strip() for l in self.log_path.read_text(encoding="utf-8").splitlines() if l.strip()]
        if not lines:
            return "0" * 64
        try:
            last_record = json.loads(lines[-1])
            return last_record.get("hash", "0" * 64)
        except Exception:
            return "0" * 64

    def append_event(self, event_type: str, data: dict) -> dict:
        prev_hash = self._get_last_hash()
        timestamp = datetime.now(timezone.utc).isoformat()

        record = {"timestamp": timestamp, "event": event_type, "data": data, "previous_hash": prev_hash}

        # Calcul du hash canonique de l'enregistrement
        canonical_str = json.dumps(record, sort_keys=True)
        record_hash = hashlib.sha256(canonical_str.encode("utf-8")).hexdigest()
        record["hash"] = record_hash

        with open(self.log_path, "a", encoding="utf-8") as f:
            f.write(json.dumps(record, ensure_ascii=False) + "\n")
        return record

    def verify_chain(self) -> bool:
        if not self.log_path.exists():
            return True
        lines = [l.strip() for l in self.log_path.read_text(encoding="utf-8").splitlines() if l.strip()]
        expected_prev = "0" * 64

        for line in lines:
            try:
                record = json.loads(line)
            except Exception:
                return False

            if record.get("previous_hash") != expected_prev:
                return False

            stored_hash = record.pop("hash", None)
            if not stored_hash:
                return False

            canonical_str = json.dumps(record, sort_keys=True)
            calc_hash = hashlib.sha256(canonical_str.encode("utf-8")).hexdigest()

            if calc_hash != stored_hash:
                return False

            expected_prev = stored_hash
        return True
