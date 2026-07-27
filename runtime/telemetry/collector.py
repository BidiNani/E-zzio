import threading
from typing import List, Dict, Any, Optional
from runtime.telemetry.metrics import ExecutionMetric
from runtime.telemetry.events import TelemetryEvent
from runtime.telemetry.storage import TelemetryStorage

class TelemetryCollector:
    """Collecteur passif hybride : buffer RAM ultra-rapide + persistance SQLite isolée."""
    _instance = None
    _lock = threading.Lock()

    def __new__(cls, storage: Optional[TelemetryStorage] = None):
        with cls._lock:
            if cls._instance is None:
                cls._instance = super(TelemetryCollector, cls).__new__(cls)
                cls._instance._metrics: List[ExecutionMetric] = []
                cls._instance._events: List[TelemetryEvent] = []
                cls._instance._storage = storage or TelemetryStorage()
                cls._instance._internal_lock = threading.Lock()
            return cls._instance

    def record_execution(self, metric: ExecutionMetric) -> None:
        with self._internal_lock:
            self._metrics.append(metric)
            if self._storage:
                try:
                    self._storage.save_metric(
                        exec_id=metric.exec_id,
                        action_name=metric.action_name,
                        status=metric.status,
                        duration_ms=metric.duration_ms,
                        cost=metric.cost,
                        risk_level=metric.risk_level,
                        category=metric.category
                    )
                except Exception as e:
                    # Enregistrement d'un événement d'échec de télémétrie en mémoire sans crash
                    self._events.append(TelemetryEvent(
                        payload={"error": f"TELEMETRY_STORAGE_FAILURE: {str(e)}"}
                    ))

    def record_event(self, event: TelemetryEvent) -> None:
        with self._internal_lock:
            self._events.append(event)
            if self._storage:
                try:
                    self._storage.save_event(
                        event_id=event.event_id,
                        event_type=event.event_type.value if hasattr(event.event_type, 'value') else str(event.event_type),
                        payload=event.payload,
                        timestamp=event.timestamp
                    )
                except Exception as e:
                    pass

    def get_summary(self, persistent: bool = True) -> Dict[str, Any]:
        with self._internal_lock:
            if persistent and self._storage:
                return self._storage.get_summary()

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
            if self._storage:
                self._storage.clear()
