import json
import hashlib
import threading
import os
from pathlib import Path
import time

class HardwareEvidenceLedger:
    def __init__(self, ledger_file: Path):
        self.ledger_file = ledger_file
        self._lock = threading.Lock()
        
    def _deterministic_hash(self, snapshot: dict) -> str:
        data_to_hash = {
            "hardware": snapshot.get("hardware"),
            "runtime": snapshot.get("runtime"),
            "previous_hash": snapshot.get("previous_hash")
        }
        encoded = json.dumps(data_to_hash, sort_keys=True).encode("utf-8")
        return hashlib.sha256(encoded).hexdigest()

    def append_snapshot(self, hardware_state: dict, runtime_state: dict):
        with self._lock:
            prev_hash = self._get_last_hash()
            snapshot = {
                "timestamp": time.time(),
                "hardware": hardware_state,
                "runtime": runtime_state,
                "previous_hash": prev_hash
            }
            current_hash = self._deterministic_hash(snapshot)
            snapshot["current_hash"] = current_hash
            
            with open(self.ledger_file, "a", encoding="utf-8") as f:
                f.write(json.dumps(snapshot, ensure_ascii=False) + "\n")
                f.flush()
                os.fsync(f.fileno())
            return current_hash

    def _get_last_hash(self) -> str:
        if not self.ledger_file.exists(): return "0" * 64
        with open(self.ledger_file, "r", encoding="utf-8") as f:
            lines = [line.strip() for line in f if line.strip()]
            if not lines: return "0" * 64
            try:
                return json.loads(lines[-1])["current_hash"]
            except (KeyError, json.JSONDecodeError):
                return "0" * 64

    def verify_chain(self) -> bool:
        """Vérifie l'intégrité de la chaîne entière (Défensif)."""
        if not self.ledger_file.exists(): return True
        expected_prev = "0" * 64
        
        try:
            with open(self.ledger_file, "r", encoding="utf-8") as f:
                for line in f:
                    if not line.strip(): continue
                    entry = json.loads(line)
                    
                    # Validation défensive des champs obligatoires
                    if "previous_hash" not in entry or "current_hash" not in entry:
                        return False
                        
                    if entry["previous_hash"] != expected_prev:
                        return False
                    
                    if self._deterministic_hash(entry) != entry["current_hash"]:
                        return False
                        
                    expected_prev = entry["current_hash"]
            return True
        except (json.JSONDecodeError, KeyError, OSError):
            return False
