from pathlib import Path
import json
import time
import hashlib

class MemoryEventStoreV452:
    GENESIS_HASH = "0" * 64

    def __init__(self, path="events.jsonl", quarantine_path="events_quarantine.jsonl"):
        self.path = Path(path)
        self.quarantine_path = Path(quarantine_path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.quarantine_path.parent.mkdir(parents=True, exist_ok=True)
        self.integrity_status = "UNKNOWN"
        self.integrity_error = None
        self.checked_events_count = 0
        self._validate_on_boot()

    def _log_quarantine(self, line_content: str, reason: str):
        record = {
            "timestamp": time.time(),
            "type": "CRASH_WRITE_RECOVERED",
            "details": {"source": self.path.name, "reason": reason, "truncated_content": line_content},
            "version": "4.5.2"
        }
        try:
            with self.quarantine_path.open("a", encoding="utf-8") as f:
                f.write(json.dumps(record, ensure_ascii=False) + "\n")
        except Exception:
            pass

    def _validate_on_boot(self):
        try:
            if not self.path.exists():
                self.integrity_status = "VALID"
                self.checked_events_count = 0
                return
            raw_text = self.path.read_text(encoding="utf-8")
            lines = raw_text.splitlines()
            valid_lines = []
            for idx, line in enumerate(lines):
                if not line.strip():
                    continue
                try:
                    json.loads(line)
                    valid_lines.append(line)
                except json.JSONDecodeError as e:
                    if idx == len(lines) - 1:
                        self._log_quarantine(line, "TRUNCATED_JSON_AT_EOF")
                        self.path.write_text("\n".join(valid_lines) + ("\n" if valid_lines else ""), encoding="utf-8")
                    else:
                        self.integrity_status = "FAILED"
                        self.integrity_error = f"HISTORICAL_CHAIN_COMPROMISE at line {idx}: {e}"
                        return
            if self.integrity_status == "FAILED":
                return
            self.checked_events_count = len(valid_lines)
            valid, msg = self.validate_chain()
            if valid:
                self.integrity_status = "VALID"
                self.integrity_error = None
            else:
                self.integrity_status = "FAILED"
                self.integrity_error = msg
        except Exception as e:
            self.integrity_status = "FAILED"
            self.integrity_error = str(e)

    def append(self, event_type: str, payload: dict) -> dict:
        if self.integrity_status != "VALID":
            raise RuntimeError("Store not valid")
        prev_hash = self.GENESIS_HASH
        if self.path.exists():
            lines = [l for l in self.path.read_text(encoding="utf-8").splitlines() if l.strip()]
            if lines:
                prev_hash = json.loads(lines[-1]).get("hash", self.GENESIS_HASH)
        event = {
            "schema": "4.5.2",
            "timestamp": time.time(),
            "type": event_type,
            "payload": payload,
            "previous_hash": prev_hash
        }
        raw = json.dumps(event, sort_keys=True, ensure_ascii=False).encode("utf-8")
        event["hash"] = hashlib.sha256(raw).hexdigest()
        with self.path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(event, ensure_ascii=False) + "\n")
        self.checked_events_count += 1
        return event

    def validate_chain(self) -> tuple:
        if not self.path.exists():
            return True, "Store empty"
        lines = [l for l in self.path.read_text(encoding="utf-8").splitlines() if l.strip()]
        if not lines:
            return True, "Store empty"
        expected_prev = self.GENESIS_HASH
        for idx, line in enumerate(lines):
            event = json.loads(line)
            if event.get("previous_hash") != expected_prev:
                return False, f"Chain broken at index {idx}"
            stored_hash = event.get("hash")
            ev_copy = dict(event)
            ev_copy.pop("hash", None)
            calc_hash = hashlib.sha256(json.dumps(ev_copy, sort_keys=True, ensure_ascii=False).encode("utf-8")).hexdigest()
            if calc_hash != stored_hash:
                return False, f"Hash mismatch at index {idx}"
            expected_prev = stored_hash
        return True, f"Chain valid ({len(lines)} events)"