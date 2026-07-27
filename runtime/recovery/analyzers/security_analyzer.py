from runtime.recovery.analyzers.base import BaseAnalyzer
from runtime.recovery.contracts import Finding
from typing import List, Dict, Any

class SecurityAnalyzer(BaseAnalyzer):
    def analyze(self, context: Dict[str, Any]) -> List[Finding]:
        findings = []
        if not context.get("context_signature_valid", True):
            findings.append(Finding(
                type="HMAC_TAMPERING_DETECTED",
                confidence=1.0,
                severity="CRITICAL",
                evidence={"error": "ExecutionContext HMAC signature invalid or altered."}
            ))
        return findings
