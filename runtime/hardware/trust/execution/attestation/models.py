from dataclasses import dataclass, field
from enum import Enum
from typing import List, Dict, Any

class AttestationVerdict(Enum):
    COMPLIANT = "COMPLIANT"
    VIOLATION_AFFINITY = "VIOLATION_AFFINITY"
    VIOLATION_RESOURCE = "VIOLATION_RESOURCE"
    ABORTED_CRASH = "ABORTED_CRASH"
    ATTESTATION_FAILED = "ATTESTATION_FAILED"
    OS_UNAVAILABLE = "OS_UNAVAILABLE"
    MEASUREMENT_TIMEOUT = "MEASUREMENT_TIMEOUT"
    LEDGER_WRITE_FAILED = "LEDGER_WRITE_FAILED"
    NON_COMPLIANT = "NON_COMPLIANT"

@dataclass(frozen=True)
class ObservationSnapshot:
    pid: int
    actual_affinity_mask: List[int]
    active_threads: int
    peak_ram_mb: float
    os_enforcement_verified: bool
    is_alive: bool

@dataclass(frozen=True)
class ExecutionReceipt:
    sequence_id: int
    previous_receipt_hash: str
    receipt_id: str
    execution_id: str
    workload_id: str
    capability_token_id: str
    admission_grant_hash: str
    capability_contract_hash: str
    model_identity: Dict[str, Any]
    contract: Dict[str, Any]
    observation: Dict[str, Any]
    attestation_verdict: str
    violations: List[str]
    timestamps: Dict[str, float]
    signature: str
