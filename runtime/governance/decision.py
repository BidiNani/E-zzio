import json
import hashlib
import hmac
from dataclasses import dataclass, asdict
from typing import Dict, Any

@dataclass(frozen=True)
class DecisionContract:
    decision_id: str
    source: str
    action: str
    target: str
    declared_risk_score: float
    resource_cost: Dict[str, Any]
    rollback_required: bool
    timestamp: str
    signature: str

    def compute_fingerprint(self) -> str:
        payload = asdict(self)
        payload.pop("signature", None)
        canonical_str = json.dumps(payload, sort_keys=True, separators=(',', ':'))
        return hashlib.sha256(canonical_str.encode("utf-8")).hexdigest()

    def verify_integrity(self) -> bool:
        return hmac.compare_digest(self.signature, self.compute_fingerprint())
