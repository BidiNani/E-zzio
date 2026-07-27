from runtime.recovery.analyzers.base import BaseAnalyzer
from typing import List, Dict, Any

class SecurityAnalyzer(BaseAnalyzer):
    def analyze(self, context: Dict[str, Any]) -> List[str]:
        results = []
        if not context.get("context_signature_valid", True):
            results.append("SECURITY_VIOLATION: Context signature tampered or invalid HMAC.")
        return results
