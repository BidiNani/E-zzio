import os
import time
import json
from pathlib import Path

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
            "version": "4.5.1"
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
                    "version": "4.5.1"
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
