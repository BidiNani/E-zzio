from runtime.recovery.executor.base import BaseActionExecutor
from typing import Dict, Any, Optional

class ScalingExecutor(BaseActionExecutor):
    def __init__(self, target_collector: Optional[Any] = None):
        self.target_collector = target_collector

    def execute(self, parameters: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        new_batch = parameters.get("new_batch_size", 200)
        prev_batch = 50
        if self.target_collector and hasattr(self.target_collector, "batch_size"):
            prev_batch = self.target_collector.batch_size
            self.target_collector.batch_size = new_batch

        return {
            "status": "SUCCESS",
            "target": "collector.batch_size",
            "previous_state": {"batch_size": prev_batch},
            "new_state": {"batch_size": new_batch}
        }

    def restore(self, previous_state: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        old_batch = previous_state.get("batch_size", 50)
        if self.target_collector and hasattr(self.target_collector, "batch_size"):
            self.target_collector.batch_size = old_batch
        return {"status": "RESTORED", "restored_batch_size": old_batch}
