from runtime.recovery.executor.base import BaseActionExecutor
from typing import Dict, Any

class QuarantineExecutor(BaseActionExecutor):
    def __init__(self):
        self.quarantined_handlers = set()

    def execute(self, parameters: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        handler = context.get("action_name", "unknown")
        self.quarantined_handlers.add(handler)
        return {
            "status": "SUCCESS",
            "target": "quarantine_registry",
            "quarantined_handler": handler,
            "previous_state": {"is_quarantined": False, "handler": handler},
            "new_state": {"is_quarantined": True, "handler": handler},
            "scope": parameters.get("scope", "immediate_isolation")
        }

    def restore(self, previous_state: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        handler = previous_state.get("handler", context.get("action_name"))
        if handler in self.quarantined_handlers:
            self.quarantined_handlers.remove(handler)
        return {"status": "RESTORED", "unquarantined_handler": handler}
