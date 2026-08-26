from typing import Dict, Any


class FeedbackEngine:
    """Processes execution results to calculate confidence adjustments and learning deltas."""

    @staticmethod
    def process_feedback(execution_result: Dict[str, Any]) -> Dict[str, Any]:
        status = execution_result.get("status")
        if status == "SUCCESS":
            return {"status": "LEARNED", "confidence_delta": 0.05, "success": True}
        elif status == "BLOCKED":
            return {"status": "RESTRICTED", "confidence_delta": -0.02, "success": False}
        else:
            return {"status": "FAILED", "confidence_delta": -0.1, "success": False}
