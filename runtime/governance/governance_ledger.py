import json
import hashlib
from pathlib import Path
from datetime import datetime

class GovernanceLedger:
    def __init__(self, ledger_path: Path):
        self.ledger_path = ledger_path

    def _get_last_hash(self) -> str:
        if not self.ledger_path.exists(): return "0" * 64
        with open(self.ledger_path, "r", encoding="utf-8") as f:
            lines = f.readlines()
            if not lines: return "0" * 64
            return json.loads(lines[-1]).get("current_hash")

    def log_event(self, event_type: str, decision_id: str, details: dict):
        prev_hash = self._get_last_hash()
        record = {
            "timestamp": datetime.now().isoformat(),
            "event_type": event_type,
            "decision_id": decision_id,
            "previous_hash": prev_hash,
            "details": details
        }
        # Calcul du hash actuel
        record_str = json.dumps(record, sort_keys=True)
        record["current_hash"] = hashlib.sha256((prev_hash + record_str).encode()).hexdigest()
        
        with open(self.ledger_path, "a", encoding="utf-8") as f:
            f.write(json.dumps(record, ensure_ascii=False) + "\n")
