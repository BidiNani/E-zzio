import queue
import threading
from typing import Any, Callable, Optional
from runtime.recovery.contracts import IncidentBundle

class RecoveryEventBus:
    """Bus d'événements asynchrone isolant la boucle de récupération du thread principal."""

    def __init__(self, incident_processor: Optional[Callable[[IncidentBundle], Any]] = None):
        self.incident_processor = incident_processor
        self._queue = queue.Queue(maxsize=1000)
        self._worker_thread = None
        self._stop_event = threading.Event()

    def start(self):
        self._stop_event.clear()
        self._worker_thread = threading.Thread(target=self._worker, daemon=True, name="RecoveryEventWorker")
        self._worker_thread.start()

    def stop(self):
        if self._worker_thread and self._worker_thread.is_alive():
            self._queue.put(None)
            self._worker_thread.join(timeout=3.0)

    def publish_incident(self, bundle: IncidentBundle):
        try:
            self._queue.put_nowait(bundle)
        except queue.Full:
            pass  # En cas de congestion extrême de la queue de recovery

    def _worker(self):
        while not self._stop_event.is_set():
            try:
                bundle = self._queue.get(timeout=0.1)
                if bundle is None:
                    break
                if self.incident_processor:
                    self.incident_processor(bundle)
            except queue.Empty:
                pass
