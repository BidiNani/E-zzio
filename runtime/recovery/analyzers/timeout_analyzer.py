from runtime.recovery.analyzers.base import BaseAnalyzer
from typing import List, Dict, Any

class TimeoutAnalyzer(BaseAnalyzer):
    def analyze(self, context: Dict[str, Any]) -> List[str]:
        results = []
        if context.get("category") == "EXTERNAL_TIMEOUT":
            results.append("INFRASTRUCTURE: Target tool/handler exceeded SLA execution window.")
        return results
