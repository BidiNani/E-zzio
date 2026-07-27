import threading
from typing import List, Dict, Any
from runtime.telemetry.metrics import ExecutionMetric
from runtime.telemetry.events import TelemetryEvent

class TelemetryCollector:
    """Collecteur passif et thread-safe isolant la mesure de performance du Kernel."""
    _instance = None
    _lock = threading.Lock()

    def __new__(cls):
        with cls._lock:
            if cls._instance is None:
                cls._instance = super(TelemetryCollector, cls).__new__(cls)
                cls._instance._metrics: List[ExecutionMetric] = []
                cls._instance._events: List[TelemetryEvent] = []
                cls._instance._internal_lock = threading.Lock()
            return cls._instance

    def record_execution(self, metric: ExecutionMetric) -> None:
        with self._internal_lock:
            self._metrics.append(metric)

    def record_event(self, event: TelemetryEvent) -> None:
        with self._internal_lock:
            self._events.append(event)

    def get_summary(self) -> Dict[str, Any]:
        with self._internal_lock:
            total = len(self._metrics)
            if total == 0:
                return {
                    "total_executions": 0,
                    "success_rate": 1.0,
                    "mean_latency_ms": 0.0,
                    "error_breakdown": {}
                }

            successes = sum(1 for m in self._metrics if m.status == "SUCCESS")
            total_duration = sum(m.duration_ms for m in self._metrics)

            error_categories: Dict[str, int] = {}
            for m in self._metrics:
                if m.category:
                    error_categories[m.category] = error_categories.get(m.category, 0) + 1

            return {
                "total_executions": total,
                "success_rate": round(successes / total, 4),
                "mean_latency_ms": round(total_duration / total, 2),
                "error_breakdown": error_categories
            }

    def reset(self) -> None:
        with self._internal_lock:
            self._metrics.clear()
            self._events.clear()
