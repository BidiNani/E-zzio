import os
import json
import shutil
from pathlib import Path


class AtomicEventWriter:
    def __init__(self, store_path: str):
        self.path = Path(store_path)
        self.pending_path = self.path.with_suffix(".pending")
        self.bak_path = self.path.with_suffix(".bak")
        self.commit_log_path = self.path.parent / "events.commit.log"

        # Auto-récupération obligatoire à l'instanciation
        self._recover_interrupted_swap()

    def _log_state(self, state: str):
        try:
            log_data = {"state": state}
            with open(self.commit_log_path, "w", encoding="utf-8") as f:
                json.dump(log_data, f)
                f.flush()
                os.fsync(f.fileno())
        except Exception:
            pass

    def _recover_interrupted_swap(self):
        """Restaure l'état du store si un crash s'est produit au milieu d'une transaction."""
        # Purge tolérante du log de commit s'il est corrompu
        if self.commit_log_path.exists():
            try:
                with open(self.commit_log_path, "r", encoding="utf-8") as f:
                    json.load(f)
            except Exception:
                try:
                    self.commit_log_path.unlink()
                except Exception:
                    pass

        # Restauration de la fenêtre de crash
        if not self.path.exists():
            if self.pending_path.exists() and self.pending_path.stat().st_size > 0:
                os.replace(self.pending_path, self.path)
            elif self.bak_path.exists():
                os.replace(self.bak_path, self.path)

    def write_event(self, event_data: dict) -> bool:
        """Exécute une écriture transactionnelle append-only atomique."""
        try:
            event_json = json.dumps(event_data, ensure_ascii=False)
            self._log_state("PREPARED")

            # 1. Duplication de l'existant vers pending si le store est présent
            if self.path.exists():
                shutil.copy2(self.path, self.pending_path)

            # 2. Écriture du nouvel événement en mode append + fsync
            with open(self.pending_path, "a", encoding="utf-8") as f:
                f.write(event_json + "\n")
                f.flush()
                os.fsync(f.fileno())

            self._log_state("FLUSHED")

            # 3. Backup de l'existant
            if self.path.exists():
                os.replace(self.path, self.bak_path)

            # 4. Replacement atomique final
            os.replace(self.pending_path, self.path)
            self._log_state("COMMITTED")

            # Nettoyage log
            if self.commit_log_path.exists():
                try:
                    self.commit_log_path.unlink()
                except Exception:
                    pass

            return True
        except Exception:
            self._log_state("FAILED")
            return False
