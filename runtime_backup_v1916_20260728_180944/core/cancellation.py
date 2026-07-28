import time
import threading

class CancellationToken:
    """Jeton d'annulation avec limite de temps inhérente (Deadline)."""
    def __init__(self, timeout_sec: float = None):
        self._event = threading.Event()
        self.deadline = time.time() + timeout_sec if timeout_sec else None

    def cancel(self):
        self._event.set()

    def is_cancelled(self) -> bool:
        return self._event.is_set()

    def check(self):
        if self.is_cancelled():
            raise InterruptedError("Opération annulée par demande explicite.")
        if self.deadline and time.time() > self.deadline:
            raise InterruptedError(f"Opération annulée : Délai d'exécution dépassé.")