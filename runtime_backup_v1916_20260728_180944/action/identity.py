from dataclasses import dataclass
from typing import Optional

@dataclass(frozen=True)
class ExecutionIdentity:
    """Hierarchical trace identity for DAG graph visualization and causal tracking."""
    root_trace_id: str
    execution_id: str
    parent_execution_id: Optional[str] = None
    depth: int = 0

    def derive_child(self, child_execution_id: str) -> 'ExecutionIdentity':
        return ExecutionIdentity(
            root_trace_id=self.root_trace_id,
            execution_id=child_execution_id,
            parent_execution_id=self.execution_id,
            depth=self.depth + 1
        )
