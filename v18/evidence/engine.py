import uuid
import time
from enum import Enum
from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field

class FactCertainty(str, Enum):
    ASSERTION = "ASSERTION"
    OBSERVATION = "OBSERVATION"
    EVIDENCE = "EVIDENCE"
    VERIFIED_FACT = "VERIFIED_FACT"

class EvidenceArtifact(BaseModel):
    evidence_id: str
    source_task_id: str
    certainty: FactCertainty
    claim: str
    proof_payload: Dict[str, Any]
    verified_by: Optional[str] = None
    created_at: float = Field(default_factory=time.time)

class EvidenceVault:
    def __init__(self):
        self._vault: Dict[str, EvidenceArtifact] = {}

    def record_evidence(self, task_id: str, claim: str, payload: Dict[str, Any], certainty: FactCertainty = FactCertainty.EVIDENCE) -> EvidenceArtifact:
        eid = f"ev_{uuid.uuid4().hex[:10]}"
        artifact = EvidenceArtifact(
            evidence_id=eid,
            source_task_id=task_id,
            certainty=certainty,
            claim=claim,
            proof_payload=payload
        )
        self._vault[eid] = artifact
        return artifact

    def get_evidence(self, eid: str) -> Optional[EvidenceArtifact]:
        return self._vault.get(eid)

global_evidence_vault = EvidenceVault()
