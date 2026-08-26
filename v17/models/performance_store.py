import time
import threading
from typing import Dict, Any, List, Optional
from pydantic import BaseModel

class ExecutionMetric(BaseModel):
    model_id: str
    task_type: str
    latency_ms: float
    success: bool
    quality_observed: float
    timestamp: float

class ModelPerformanceStore:
    def __init__(self, max_history: int = 1000):
        self.max_history = max_history
        self._metrics: List[ExecutionMetric] = []
        self._lock = threading.Lock()

    def record_execution(self, model_id: str, task_type: str, latency_ms: float, success: bool = True, quality: float = 1.0):
        metric = ExecutionMetric(
            model_id=model_id,
            task_type=task_type,
            latency_ms=latency_ms,
            success=success,
            quality_observed=quality,
            timestamp=time.time()
        )
        with self._lock:
            if len(self._metrics) >= self.max_history:
                self._metrics.pop(0)
            self._metrics.append(metric)

    def get_model_stats(self, model_id: str) -> Dict[str, Any]:
        with self._lock:
            relevant = [m for m in self._metrics if m.model_id == model_id]
            if not relevant:
                return {"total": 0, "success_rate": 1.0, "avg_latency_ms": 0.0}
            total = len(relevant)
            successes = sum(1 for m in relevant if m.success)
            avg_lat = sum(m.latency_ms for m in relevant) / total
            return {
                "total": total,
                "success_rate": round(successes / total, 3),
                "avg_latency_ms": round(avg_lat, 1)
            }

global_performance_store = ModelPerformanceStore()
