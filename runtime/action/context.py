import os
import hmac
import hashlib
from dataclasses import dataclass, field, replace, asdict
from typing import Dict, Any, Tuple, Optional, Union, List


def get_hmac_secret() -> bytes:
    """Récupère le secret HMAC en exigeant une variable d'environnement en production."""
    secret = os.environ.get("EZZIO_HMAC_SECRET")
    env = os.environ.get("EZZIO_ENV", "development")
    if not secret:
        if env == "production":
            raise RuntimeError("CRITICAL: EZZIO_HMAC_SECRET is missing in production environment!")
        return b"ezzio_kernel_default_secure_fallback_key_2026"
    return secret.encode("utf-8")


SYSTEM_HMAC_SECRET = get_hmac_secret()


class SecurityError(Exception):
    """Raised when context tampering is detected."""

    pass


@dataclass(frozen=True)
class ExecutionContext:
    """Immutable execution context protected by strict HMAC-SHA256 signatures."""

    @property
    def state(self):
        if not hasattr(self, "_state"):
            object.__setattr__(self, "_state", {})
        return self._state

    @state.setter
    def state(self, value):
        object.__setattr__(self, "_state", value)

    trace_id: str
    parent_trace_id: Optional[str] = None
    agent_id: str = "ezzio-core"
    permissions: Tuple[str, ...] = ("*",)
    budget_remaining: int = 100
    signature: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        if isinstance(self.permissions, (list, set)):
            object.__setattr__(self, "permissions", tuple(self.permissions))
        if not self.signature:
            sig = self.compute_signature()
            object.__setattr__(self, "signature", sig)
        self.validate_structure()

    def compute_signature(self) -> str:
        payload_str = f"{self.trace_id}|{self.parent_trace_id}|{self.agent_id}|{','.join(sorted(self.permissions))}|{self.budget_remaining}"
        return hmac.new(SYSTEM_HMAC_SECRET, payload_str.encode("utf-8"), hashlib.sha256).hexdigest()

    def verify_signature(self) -> bool:
        return hmac.compare_digest(self.signature, self.compute_signature())

    def validate_structure(self):
        if not self.trace_id or not isinstance(self.trace_id, str):
            raise ValueError("ExecutionContext.trace_id must be a non-empty string.")
        if not self.agent_id or not isinstance(self.agent_id, str):
            raise ValueError("ExecutionContext.agent_id must be a non-empty string.")
        if self.budget_remaining < 0:
            raise ValueError(f"ExecutionContext.budget_remaining cannot be negative (got {self.budget_remaining}).")

    def consume_budget(self, cost: int) -> "ExecutionContext":
        new_budget = self.budget_remaining - cost
        if new_budget < 0:
            raise ValueError(f"Execution budget exceeded: remaining {self.budget_remaining} < cost {cost}.")
        return replace(self, budget_remaining=new_budget, signature="")

    def derive_child(self, child_trace_id: str, new_permissions: Optional[Union[Tuple[str, ...], List[str]]] = None) -> "ExecutionContext":
        perms = tuple(new_permissions) if new_permissions is not None else self.permissions
        return replace(self, trace_id=child_trace_id, parent_trace_id=self.trace_id, permissions=perms, signature="")

    def to_dict(self) -> Dict[str, Any]:
        data = asdict(self)
        data["permissions"] = list(self.permissions)
        return data

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ExecutionContext":
        if "permissions" in data and isinstance(data["permissions"], list):
            data["permissions"] = tuple(data["permissions"])
        return cls(**data)
