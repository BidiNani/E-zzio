from runtime.recovery.analyzers.base import BaseAnalyzer
from runtime.recovery.contracts import Finding
from typing import List, Dict, Any


class TimeoutAnalyzer(BaseAnalyzer):
    def analyze(self, context: Dict[str, Any]) -> List[Finding]:
        findings = []
        if context.get("category") == "EXTERNAL_TIMEOUT":
            findings.append(
                Finding(
                    type="EXTERNAL_SLA_EXCEEDED",
                    confidence=0.95,
                    severity="HIGH",
                    evidence={"details": context.get("error_details", "Timeout exceeded SLA window")},
                )
            )
        return findings
