from pathlib import Path
import json
import time
import hashlib
import os

def _is_process_alive(pid: int) -> bool:
    if pid <= 0:
        return False
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
    except Exception:
        return False
    return True

class SimpleFileLock:
    def __init__(self, lock_path, security_log_path=None, timeout=5.0, max_age=60.0):
        self.lock_path = Path(lock_path)
        self.security_path = Path(security_log_path) if security_log_path else None
        self.timeout = timeout
        self.max_age = max_age
        self.pid = os.getpid()

    def _log_security(self, event_type: str, details: dict):
        if not self.security_path:
            return
        sec_event = {
            "timestamp": time.time(),
            "type": event_type,
            "details": details,
            "version": "4.5.2"
        }
        try:
            self.security_path.parent.mkdir(parents=True, exist_ok=True)
            with self.security_path.open("a", encoding="utf-8") as f:
                f.write(json.dumps(sec_event, ensure_ascii=False) + "\n")
        except Exception:
            pass

    def __enter__(self):
        start = time.time()
        while True:
            try:
                fd = os.open(self.lock_path, os.O_CREAT | os.O_EXCL | os.O_RDWR)
                meta = {
                    "pid": self.pid,
                    "created": time.time(),
                    "host": os.environ.get("COMPUTERNAME", "unknown"),
                    "version": "4.5.2"
                }
                os.write(fd, json.dumps(meta).encode("utf-8"))
                os.close(fd)
                return self
            except FileExistsError:
                if time.time() - start > self.timeout:
                    raise TimeoutError(f"Could not acquire lock on {self.lock_path}")
                if self._inspect_and_clear_if_stale():
                    continue
                time.sleep(0.05)

    def _inspect_and_clear_if_stale(self) -> bool:
        try:
            if not self.lock_path.exists():
                return True
            content = self.lock_path.read_text(encoding="utf-8").strip()
            if not content:
                self.lock_path.unlink(missing_ok=True)
                self._log_security("STALE_LOCK_RECOVERED", {"reason": "empty_file", "action": "removed"})
                return True
            data = json.loads(content)
            lock_pid = data.get("pid", 0)
            created_at = data.get("created", 0.0)
            age = time.time() - created_at
            if not _is_process_alive(lock_pid):
                self.lock_path.unlink(missing_ok=True)
                self._log_security("STALE_LOCK_RECOVERED", {"old_pid": lock_pid, "age_seconds": age, "reason": "dead_pid", "action": "removed"})
                return True
            return False
        except (json.JSONDecodeError, Exception) as e:
            try:
                self.lock_path.unlink(missing_ok=True)
                self._log_security("STALE_LOCK_RECOVERED", {"reason": f"corrupted: {e}", "action": "removed"})
                return True
            except Exception:
                return False

    def __exit__(self, exc_type, exc_val, exc_tb):
        try:
            if self.lock_path.exists():
                content = self.lock_path.read_text(encoding="utf-8")
                data = json.loads(content)
                if data.get("pid") == self.pid:
                    self.lock_path.unlink()
        except Exception:
            pass

class MemoryEventStore:
    ALLOWED_TYPES = {
        "SKILL_EXECUTED",
        "SKILL_FAILED",
        "SYSTEM_EVENT",
        "RECOVERY_EVENT",
        "SECURITY_EVENT"
    }
    GENESIS_HASH = "0" * 64

    def __init__(self, path="runtime/memory/events.jsonl", security_log_path="runtime/memory/security_events.jsonl", snapshot_path="runtime/memory/snapshot.json", archive_dir="runtime/memory/archive", quarantine_path="runtime/memory/events_quarantine.jsonl"):
        self.path = Path(path)
        self.security_path = Path(security_log_path)
        self.snapshot_path = Path(snapshot_path)
        self.archive_dir = Path(archive_dir)
        self.quarantine_path = Path(quarantine_path)
        self.lock_path = self.path.with_suffix(".lock")
        
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.security_path.parent.mkdir(parents=True, exist_ok=True)
        self.snapshot_path.parent.mkdir(parents=True, exist_ok=True)
        self.archive_dir.mkdir(parents=True, exist_ok=True)
        self.quarantine_path.parent.mkdir(parents=True, exist_ok=True)
        
        self.integrity_status = "UNKNOWN"
        self.integrity_error = None
        self.checked_events_count = 0
        
        self._validate_on_boot()

    def _log_security_event(self, event_type: str, details: dict):
        sec_event = {
            "timestamp": time.time(),
            "type": event_type,
            "details": details,
            "version": "4.5.2"
        }
        try:
            with self.security_path.open("a", encoding="utf-8") as f:
                f.write(json.dumps(sec_event, ensure_ascii=False) + "\n")
        except Exception:
            pass

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
                self.integrity_error = None
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
                        self._log_security_event("MEMORY_CHAIN_COMPROMISED", {
                            "status": "FAILED",
                            "error": self.integrity_error
                        })
                        return

            if self.integrity_status == "FAILED":
                return

            self.checked_events_count = len(valid_lines)
            valid, msg = self.validate_chain()
            if valid:
                self.integrity_status = "VALID"
                self.integrity_error = None
                self._log_security_event("MEMORY_CHAIN_VALIDATION", {
                    "status": "VALID",
                    "checked_events": self.checked_events_count
                })
            else:
                self.integrity_status = "FAILED"
                self.integrity_error = msg
                self._log_security_event("MEMORY_CHAIN_COMPROMISED", {
                    "status": "FAILED",
                    "error": msg
                })
        except Exception as e:
            self.integrity_status = "FAILED"
            self.integrity_error = str(e)
            self._log_security_event("MEMORY_CHAIN_COMPROMISED", {
                "status": "FAILED",
                "error": str(e)
            })

    def assert_boot_integrity(self):
        if self.integrity_status != "VALID":
            raise RuntimeError(
                f"MEMORY INTEGRITY FAILURE: events.jsonl chain invalid. Details: {self.integrity_error}"
            )

    def _get_last_hash(self) -> str:
        if not self.path.exists():
            return self.GENESIS_HASH
        try:
            lines = [l for l in self.path.read_text(encoding="utf-8").splitlines() if l.strip()]
            if not lines:
                return self.GENESIS_HASH
            last_event = json.loads(lines[-1])
            return last_event.get("hash", self.GENESIS_HASH)
        except Exception:
            return self.GENESIS_HASH

    def append(self, event_type: str, payload: dict, context: dict = None) -> dict:
        if self.integrity_status != "VALID":
            raise RuntimeError("Cannot append to memory store: Integrity status is not VALID.")

        with SimpleFileLock(self.lock_path, self.security_path):
            prev_hash = self._get_last_hash()

            event = {
                "schema": "4.5.2",
                "timestamp": time.time(),
                "type": event_type,
                "payload": payload,
                "context": context or {"interface": "cli", "version": "4.5.2"},
                "previous_hash": prev_hash
            }

            raw = json.dumps(
                event,
                sort_keys=True,
                ensure_ascii=False
            ).encode("utf-8")

            event["hash"] = hashlib.sha256(raw).hexdigest()

            with self.path.open("a", encoding="utf-8") as f:
                f.write(json.dumps(event, ensure_ascii=False) + "\n")
            
            self.checked_events_count += 1

        return event

    def recent(self, limit=10) -> list:
        if not self.path.exists():
            return []
        lines = [l for l in self.path.read_text(encoding="utf-8").splitlines() if l.strip()]
        return [json.loads(x) for x in lines[-limit:] if x.strip()]

    def validate_chain(self) -> tuple:
        if not self.path.exists():
            return True, "Store empty"
        
        lines = [l for l in self.path.read_text(encoding="utf-8").splitlines() if l.strip()]
        if not lines:
            return True, "Store empty"

        expected_prev = self.GENESIS_HASH

        for idx, line in enumerate(lines):
            try:
                event = json.loads(line)
            except json.JSONDecodeError as e:
                return False, f"JSON error at line {idx}: {e}"

            actual_prev = event.get("previous_hash", self.GENESIS_HASH)
            if actual_prev != expected_prev:
                return False, f"Chain broken at index {idx}: expected {expected_prev}, got {actual_prev}"

            stored_hash = event.get("hash")
            
            ev_copy = dict(event)
            ev_copy.pop("hash", None)
            raw = json.dumps(ev_copy, sort_keys=True, ensure_ascii=False).encode("utf-8")
            calculated_hash = hashlib.sha256(raw).hexdigest()

            if calculated_hash != stored_hash:
                return False, f"Hash mismatch at index {idx}"

            expected_prev = stored_hash

        return True, f"Chain valid ({len(lines)} events)"

    def get_health_metrics(self) -> dict:
        file_size = self.path.stat().st_size if self.path.exists() else 0
        return {
            "integrity_status": self.integrity_status,
            "integrity_error": self.integrity_error,
            "total_events": self.checked_events_count,
            "store_size_bytes": file_size,
            "last_hash": self._get_last_hash()[:16] + "...",
            "governance_version": "4.5.2"
        }