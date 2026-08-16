import os
import json
import shutil
import queue
import threading
import time
from pathlib import Path

class BatchAsyncAtomicEventWriter:
    """
    Writer asynchrone à commit par lots (Hybride Taille/Temps)
    Optimisé pour Ryzen 9 5900X et supports NVMe.
    """
    def __init__(self, store_path: str, max_batch_size: int = 500, max_batch_delay: float = 0.05):
        self.path = Path(store_path)
        self.pending_path = self.path.with_suffix(".pending")
        self.bak_path = self.path.with_suffix(".bak")
        self.commit_log_path = self.path.parent / "events.commit.log"
        
        self.max_batch_size = max_batch_size
        self.max_batch_delay = max_batch_delay
        
        self.queue = queue.Queue()
        self._stop_event = threading.Event()
        self.accepting = True
        self.closed = False
        
        # Auto-récupération initiale
        self._recover_interrupted_swap()
        
        # Démarrage du thread Commit Worker dédié au batching
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
        if not self.accepting or self.closed:
            raise RuntimeError("Tentative d'écriture sur un writer fermé ou non réceptif.")
        self.queue.put(event_data)

    def _commit_loop(self):
        while not self._stop_event.is_set() or not self.queue.empty():
            batch = []
            start_time = time.time()
            
            # Collecte par taille ou fenêtre temporelle
            while len(batch) < self.max_batch_size:
                timeout = self.max_batch_delay - (time.time() - start_time)
                if timeout <= 0:
                    break
                try:
                    item = self.queue.get(timeout=max(0.001, timeout))
                    batch.append(item)
                    self.queue.task_done()
                except queue.Empty:
                    break
            
            if not batch:
                continue

            try:
                # Sérialisation groupée du lot en lignes JSON
                batch_lines = [json.dumps(ev, ensure_ascii=False) + "\n" for ev in batch]
                
                self._log_state("PREPARED")

                # 1. Initialisation du pending avec le store existant
                if self.path.exists():
                    shutil.copy2(self.path, self.pending_path)
                else:
                    if self.pending_path.exists():
                        self.pending_path.unlink()

                # 2. Écriture en mode append du lot complet + unique fsync
                with open(self.pending_path, "a", encoding="utf-8") as f:
                    f.writelines(batch_lines)
                    f.flush()
                    os.fsync(f.fileno())

                self._log_state("FLUSHED")

                # 3. Double buffering / Backup
                if self.path.exists():
                    os.replace(self.path, self.bak_path)

                # 4. Swap atomique final
                os.replace(self.pending_path, self.path)
                self._log_state("COMMITTED")

                if self.commit_log_path.exists():
                    try:
                        self.commit_log_path.unlink()
                    except Exception:
                        pass
            except Exception:
                self._log_state("FAILED")

    def flush(self):
        while not self.queue.empty():
            time.sleep(0.01)
        time.sleep(0.05)

    def close(self):
        self.accepting = False
        self.flush()
        self._stop_event.set()
        self.worker_thread.join(timeout=3.0)
        self.closed = True
