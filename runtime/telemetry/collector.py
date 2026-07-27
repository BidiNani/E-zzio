import queue
import threading
import time
from typing import List, Dict, Any, Optional
from runtime.telemetry.metrics import ExecutionMetric
from runtime.telemetry.events import TelemetryEvent
from runtime.telemetry.storage import TelemetryStorage

class TelemetryCollector:
    """Collecteur Asynchrone Ultra-Rapide avec Rétrocompatibilité API et Métriques Industrielles."""

    def __init__(self, storage: Optional[TelemetryStorage] = None, batch_size: int = 50, flush_interval: float = 0.5):
        self.collector_version = "2.6.8.2"
        self.storage = storage
        self.batch_size = batch_size
        self.flush_interval = flush_interval
        
        self.dropped_metrics = 0
        self.dropped_events = 0
        self.flush_count = 0

        self._queue = queue.Queue(maxsize=10000)
        self._writer_thread = None

    def start(self):
        if self.storage:
            self.storage.connect()
        self._writer_thread = threading.Thread(target=self._worker, daemon=True, name="TelemetryWriter")
        self._writer_thread.start()

    def stop(self):
        if self._writer_thread and self._writer_thread.is_alive():
            self._queue.put(None)
            self._writer_thread.join(timeout=3.0)
        if self.storage:
            self.storage.close()

    def reset(self):
        with self._queue.mutex:
            self._queue.queue.clear()
        self.dropped_metrics = 0
        self.dropped_events = 0
        self.flush_count = 0

    def flush(self):
        """Purge synchrone de la queue vers la BDD."""
        batch_metrics = []
        batch_events = []
        while not self._queue.empty():
            try:
                item = self._queue.get_nowait()
                if item is None: continue
                if item[0] == 'metric': batch_metrics.append(item[1])
                elif item[0] == 'event': batch_events.append(item[1])
            except queue.Empty: break
        self._flush_batches(batch_metrics, batch_events)

    def record_execution(self, metric: ExecutionMetric) -> None:
        try:
            self._queue.put_nowait(('metric', metric))
        except queue.Full:
            self.dropped_metrics += 1

    def record_event(self, event: TelemetryEvent) -> None:
        try:
            self._queue.put_nowait(('event', event))
        except queue.Full:
            self.dropped_events += 1

    def _worker(self):
        batch_metrics = []
        batch_events = []
        last_flush = time.time()
        last_maintenance = time.time()

        while True:
            q_size = self._queue.qsize()
            if q_size > 5000: target_batch = 1000
            elif q_size > 1000: target_batch = 500
            else: target_batch = self.batch_size

            try:
                item = self._queue.get(timeout=0.1)
                if item is None:
                    break
                if item[0] == 'metric': batch_metrics.append(item[1])
                elif item[0] == 'event': batch_events.append(item[1])
            except queue.Empty: pass

            now = time.time()
            if len(batch_metrics) >= target_batch or len(batch_events) >= target_batch or (now - last_flush) > self.flush_interval:
                self._flush_batches(batch_metrics, batch_events)
                last_flush = now

            if now - last_maintenance > 86400:
                if self.storage:
                    self.storage.enforce_retention()
                    self.storage.run_maintenance()
                last_maintenance = now

        self._flush_batches(batch_metrics, batch_events)

    def _flush_batches(self, metrics: List, events: List):
        self.flush_count += 1
        if self.storage:
            if metrics:
                self.storage.save_metrics_batch(metrics)
                metrics.clear()
            if events:
                self.storage.save_events_batch(events)
                events.clear()

    def get_summary(self) -> Dict[str, Any]:
        summary = self.storage.get_summary() if self.storage else {}
        summary["collector_version"] = self.collector_version
        summary["dropped_metrics"] = self.dropped_metrics
        summary["dropped_events"] = self.dropped_events
        summary["queue_backlog"] = self._queue.qsize()
        summary["configured_batch_size"] = self.batch_size
        summary["flush_count"] = self.flush_count
        return summary

    def get_queue_size(self) -> int:
        return self._queue.qsize()
