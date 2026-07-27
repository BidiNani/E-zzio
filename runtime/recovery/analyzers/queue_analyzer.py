from runtime.recovery.analyzers.base import BaseAnalyzer
from runtime.recovery.contracts import Finding
from typing import List, Dict, Any

class QueueAnalyzer(BaseAnalyzer):
    def analyze(self, context: Dict[str, Any]) -> List[Finding]:
        findings = []
        telemetry = context.get("telemetry_snapshot", {})
        backlog = telemetry.get("queue_current_size", 0)
        dropped = telemetry.get("dropped_metrics", 0) + telemetry.get("dropped_events", 0)
        if backlog > 5000:
            findings.append(Finding(
                type="QUEUE_CONGESTION",
                confidence=0.88,
                severity="WARNING",
                evidence={"queue_backlog": backlog}
            ))
        if dropped > 0:
            findings.append(Finding(
                type="TELEMETRY_DROPS",
                confidence=0.99,
                severity="HIGH",
                evidence={"dropped_count": dropped}
            ))
        return findings
