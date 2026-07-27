from runtime.recovery.analyzers.base import BaseAnalyzer
from typing import List, Dict, Any

class QueueAnalyzer(BaseAnalyzer):
    def analyze(self, context: Dict[str, Any]) -> List[str]:
        results = []
        telemetry = context.get("telemetry_snapshot", {})
        backlog = telemetry.get("queue_current_size", 0)
        dropped = telemetry.get("dropped_metrics", 0) + telemetry.get("dropped_events", 0)
        if backlog > 5000:
            results.append(f"CONGESTION: Critical queue backlog ({backlog} pending items).")
        if dropped > 0:
            results.append(f"RESOURCE_EXHAUSTION: Telemetry drops detected ({dropped} items dropped).")
        return results
