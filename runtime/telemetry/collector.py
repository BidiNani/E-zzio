import queue
import threading
import time
from typing import List, Dict, Any, Optional
from runtime.telemetry.metrics import ExecutionMetric
from runtime.telemetry.events import TelemetryEvent
from runtime.telemetry.storage import TelemetryStorage

class TelemetryCollector:
    """Collecteur Asynchrone : Queue RAM non-bloquante, API rétrocompatible & Writer Thread."""

    def __init__(self, storage: Optional[TelemetryStorage] = None, batch_size: int = 100, flush_interval: float = 0.5):
        self.storage = storage
        self.batch_size = batch_size
        self.flush_interval = flush_interval

        self._queue = queue.Queue(maxsize=10000)
        self._stop_event = threading.Event()
        self._writer_thread = None

    def configure_storage(self, storage: Optional[TelemetryStorage]):
        """Ajuste dynamiquement le moteur de stockage."""
        self.storage = storage
        if self.storage and self._writer_thread and self._writer_thread.is_alive():
            self.storage.connect()

    def start(self):
        if self.storage:
            self.storage.connect()
        self._stop_event.clear()
        self._writer_thread = threading.Thread(target=self._worker, daemon=True, name="TelemetryWriter")
        self._writer_thread.start()

    def stop(self):
        self._stop_event.set()
        if self._writer_thread and self._writer_thread.is_alive():
            self._writer_thread.join(timeout=3.0)
        if self.storage:
            self.storage.close()

    def reset(self):
        """Purge la queue et reinitialise le stockage (compatibilité test suite)."""
        with self._queue.mutex:
            self._queue.queue.clear()
        if self.storage:
            self.storage.clear()

    def record_execution(self, metric: ExecutionMetric) -> None:
        try:
            self._queue.put_nowait(('metric', metric))
        except queue.Full:
            pass

    def record_event(self, event: TelemetryEvent) -> None:
        try:
            self._queue.put_nowait(('event', event))
        except queue.Full:
            pass

    def _worker(self):
        batch_metrics = []
        batch_events = []
        last_flush = time.time()
        retention_last_run = time.time()

        while not self._stop_event.is_set() or not self._queue.empty():
            try:
                item = self._queue.get(timeout=0.1)
                if item[0] == 'metric':
                    batch_metrics.append(item[1])
                elif item[0] == 'event':
                    batch_events.append(item[1])
            except queue.Empty:
                pass

            now = time.time()
            if len(batch_metrics) >= self.batch_size or len(batch_events) >= self.batch_size or (now - last_flush) > self.flush_interval:
                self._flush(batch_metrics, batch_events)
                last_flush = now

            if now - retention_last_run > 3600:
                if self.storage:
                    self.storage.enforce_retention()
                retention_last_run = now

        self._flush(batch_metrics, batch_events)

    def _flush(self, metrics: List, events: List):
        if not self.storage:
            metrics.clear()
            events.clear()
            return

        if metrics:
            self.storage.save_metrics_batch(metrics)
            metrics.clear()
        if events:
            self.storage.save_events_batch(events)
            events.clear()

    def get_summary(self) -> Dict[str, Any]:
        if self.storage:
            return self.storage.get_summary()
        return {
            "total_executions": 0,
            "success_rate": 1.0,
            "latency": {"mean": 0, "p50": 0, "p90": 0, "p99": 0},
            "throughput_eps": 0.0,
            "total_budget_consumed": 0.0,
            "error_breakdown": {}
        }

    def get_queue_size(self) -> int:
        return self._queue.qsize()
