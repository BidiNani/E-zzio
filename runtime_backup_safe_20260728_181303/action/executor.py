from typing import Dict, Any, Optional

class ActionExecutor:
    """Executes planned actions strictly bounded by an allowed whitelist."""
    ALLOWED_ACTIONS = [
        "STORE_KNOWLEDGE",
        "CREATE_REPORT",
        "NOTIFY_USER",
        "IGNORE"
    ]

    def __init__(self, brain=None):
        self.brain = brain

    def execute(self, plan: Dict[str, Any]) -> Dict[str, Any]:
        action = plan.get("action", "IGNORE")

        if action not in self.ALLOWED_ACTIONS:
            return {"status": "BLOCKED", "error": f"Action '{action}' is not whitelisted."}

        if action == "IGNORE":
            return {"status": "SUCCESS", "action": "IGNORE", "details": plan.get("reason", "")}

        if action == "STORE_KNOWLEDGE" and self.brain:
            try:
                self.brain.remember_fact(
                    content=f"cognitive_audit: executed plan successfully with details -> {plan}",
                    category="cognitive_audit",
                    importance=plan.get("priority", 5) / 10.0
                )
                return {"status": "SUCCESS", "action": action, "executed": True}
            except Exception as e:
                return {"status": "ERROR", "error": str(e)}

        return {"status": "SUCCESS", "action": action, "simulated": True}
