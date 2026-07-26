from dataclasses import dataclass, field, replace, asdict
from typing import Dict, Any, List, Optional

@dataclass(frozen=True)
class ExecutionContext:
    """
    Immutable execution context enforcing security, budget, causal tracing,
    automatic validation, and bidirectional serialization.
    """
    trace_id: str
    parent_trace_id: Optional[str] = None
    agent_id: str = "ezzio-core"
    permissions: List[str] = field(default_factory=lambda: ["*"])
    budget_remaining: int = 100
    metadata: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        self.validate()

    def validate(self):
        """Enforces runtime context integrity invariants."""
        if not self.trace_id or not isinstance(self.trace_id, str):
            raise ValueError("ExecutionContext.trace_id must be a non-empty string.")
        if not self.agent_id or not isinstance(self.agent_id, str):
            raise ValueError("ExecutionContext.agent_id must be a non-empty string.")
        if self.budget_remaining < 0:
            raise ValueError(f"ExecutionContext.budget_remaining cannot be negative (got {self.budget_remaining}).")

    def consume_budget(self, cost: int) -> 'ExecutionContext':
        """Returns a new context with decremented budget."""
        return replace(self, budget_remaining=self.budget_remaining - cost)

    def derive_child(self, child_trace_id: str, new_permissions: Optional[List[str]] = None) -> 'ExecutionContext':
        """Derives a child context maintaining causal lineage."""
        return replace(
            self,
            trace_id=child_trace_id,
            parent_trace_id=self.trace_id,
            permissions=list(new_permissions) if new_permissions is not None else list(self.permissions)
        )

    def to_dict(self) -> Dict[str, Any]:
        """Serializes context for EventBus transport or SQLite persistence."""
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ExecutionContext':
        """Hydrates context from a serialized dictionary."""
        return cls(**data)
