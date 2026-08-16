from dataclasses import dataclass
from runtime.hardware.trust.envelope.envelope import CapabilityEnvelope

@dataclass(frozen=True)
class ModelIdentity:
    model_id: str
    provider: str
    trust_level: str
    version_hash: str

@dataclass(frozen=True)
class ExecutionRequest:
    workload_id: str
    capability_token: CapabilityEnvelope
    model_identity: ModelIdentity
    intent: str

@dataclass(frozen=True)
class AdmissionGrant:
    status: str
    execution_id: str
    workload_id: str
    allowed_workers: int
    allowed_profile: str
    granted_constraints: dict
    issued_at: float
    capability_token_id: str
    model_origin: str
    reason: str
    signature: str
