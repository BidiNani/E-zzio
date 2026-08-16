from __future__ import annotations
from dataclasses import dataclass, field
import uuid
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from runtime.events.bus import EzzioEventBus
    from runtime.kernel.state import EzzioRuntimeState
    from runtime.security.trust import TrustRegistry
    from runtime.policy.engine import PolicyEngine
    from runtime.capabilities.registry import CapabilityRegistry
    from runtime.execution.governor import ResourceGovernor
    from runtime.execution.ledger import ExecutionLedger

@dataclass(frozen=True)
class RuntimeContext:
    """Le Cœur de l'OS unifié V4.2."""
    bus: EzzioEventBus
    state: EzzioRuntimeState
    trust: TrustRegistry
    policy: PolicyEngine
    capabilities: CapabilityRegistry
    governor: ResourceGovernor
    ledger: ExecutionLedger
    execution_id: str = field(default_factory=lambda: str(uuid.uuid4()))