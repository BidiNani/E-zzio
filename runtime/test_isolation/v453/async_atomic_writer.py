import os
import json
import shutil
import queue
import threading
from pathlib import Path

class AsyncAtomicEventWriter:
    def __init__(self, store_path: str):
        self.path = Path(store_path)
        self.pending_path = self.path.with_suffix(".pending")
        self.bak_path = self.path.with_suffix(".bak")
        self.commit_log_path = self.path.parent / "events.commit.log"
        
        self.queue = queue.Queue()
        self._stop_event = threading.Event()
        self.closed = False
        
        self._recover_interrupted_swap()
        
        self.worker_thread = threading.Thread(target=self._commit_loop, daemon=True)
        self.worker_thread.start()

    def _recover_interrupted_swap(self):
        if self.commit_log_path.exists():
            try:
                with open(self.commit_log_path, "r", encoding="utf-8") as f:
                    json.load(f)
            except Exception:
                try:
                    self.commit_log_path.unlink()
                except Exception:
                    pass

        if not self.path.exists():
            if self.pending_path.exists() and self.pending_path.stat().st_size > 0:
                os.replace(self.pending_path, self.path)
            elif self.bak_path.exists():
                os.replace(self.bak_path, self.path)

    def _log_state(self, state: str):
        try:
            log_data = {"state": state}
            with open(self.commit_log_path, "w", encoding="utf-8") as f:
                json.dump(log_data, f)
                f.flush()
                os.fsync(f.fileno())
        except Exception:
            pass

    def write_event(self, event_data: dict):
        if self.closed:
            raise RuntimeError("Tentative d'écriture sur un AsyncAtomicEventWriter fermé.")
        self.queue.put(event_data)

    def _commit_loop(self):
        while not self._stop_event.is_set() or not self.queue.empty():
            try:
                event_data = self.queue.get(timeout=0.05)
            except queue.Empty:
                continue

            try:
                event_json = json.dumps(event_data, ensure_ascii=False)
                self._log_state("PREPARED")

                if self.path.exists():
                    shutil.copy2(self.path, self.pending_path)

                with open(self.pending_path, "a", encoding="utf-8") as f:
                    f.write(event_json + "\n")
                    f.flush()
                    os.fsync(f.fileno())

                self._log_state("FLUSHED")

                if self.path.exists():
                    os.replace(self.path, self.bak_path)

                os.replace(self.pending_path, self.path)
                self._log_state("COMMITTED")

                if self.commit_log_path.exists():
                    try:
                        self.commit_log_path.unlink()
                    except Exception:
                        pass
            except Exception:
                self._log_state("FAILED")
            finally:
                self.queue.task_done()

    def flush(self):
        self.queue.join()

    def close(self):
        self.closed = True
        self.flush()
        self._stop_event.set()
        self.worker_thread.join(timeout=2.0)
