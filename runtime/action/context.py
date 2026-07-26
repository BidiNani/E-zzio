from dataclasses import dataclass, field, replace, asdict
from typing import Dict, Any, Tuple, Optional, Union, List

@dataclass(frozen=True)
class ExecutionContext:
    """
    Strictly immutable execution context supporting tuples for permissions,
    strict budget guards, causal trace derivation, and serialization.
    """
    trace_id: str
    parent_trace_id: Optional[str] = None
    agent_id: str = "ezzio-core"
    permissions: Tuple[str, ...] = ("*",)
    budget_remaining: int = 100
    metadata: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        # Conversion automatique des listes/ensembles en tuples immuables
        if isinstance(self.permissions, (list, set)):
            object.__setattr__(self, "permissions", tuple(self.permissions))
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
        """Returns a new context with decremented budget or raises ValueError if budget is exceeded."""
        new_budget = self.budget_remaining - cost
        if new_budget < 0:
            raise ValueError(f"Execution budget exceeded: remaining {self.budget_remaining} < cost {cost}.")
        return replace(self, budget_remaining=new_budget)

    def derive_child(self, child_trace_id: str, new_permissions: Optional[Union[Tuple[str, ...], List[str]]] = None) -> 'ExecutionContext':
        """Derives a child context maintaining causal lineage."""
        perms = tuple(new_permissions) if new_permissions is not None else self.permissions
        return replace(
            self,
            trace_id=child_trace_id,
            parent_trace_id=self.trace_id,
            permissions=perms
        )

    def to_dict(self) -> Dict[str, Any]:
        """Serializes context for EventBus transport or SQLite persistence."""
        data = asdict(self)
        data["permissions"] = list(self.permissions)
        return data

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ExecutionContext':
        """Hydrates context from a serialized dictionary."""
        if "permissions" in data and isinstance(data["permissions"], list):
            data["permissions"] = tuple(data["permissions"])
        return cls(**data)
