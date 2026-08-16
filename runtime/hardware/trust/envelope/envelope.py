import time
import uuid
import hashlib
import json
from dataclasses import dataclass
from runtime.hardware.trust.revocation.registry import CapabilityRevocationRegistry

@dataclass(frozen=True)
class CapabilityEnvelope:
    token_id: str
    workload_id: str
    profile: str
    constraints: dict
    issued_at: float
    expires_at: float
    trust_score_at_issue: int
    trust_state_at_issue: str
    signature: str

class EnvelopeIssuer:
    def __init__(self, revocation_registry: CapabilityRevocationRegistry, secret_seed: str = "EZZIO_HARDENED_ROOT_KEY"):
        self.revocation_registry = revocation_registry
        self.secret_seed = secret_seed

    def issue(self, workload_id: str, profile: str, constraints: dict, trust_context: dict, ttl_seconds: float = 5.0) -> CapabilityEnvelope:
        token_id = str(uuid.uuid4())
        issued_at = time.time()
        expires_at = issued_at + ttl_seconds
        score = trust_context.get("trust_score", 0)
        state = trust_context.get("state", "QUARANTINE")

        payload = {
            "token_id": token_id,
            "workload_id": workload_id,
            "profile": profile,
            "constraints": constraints,
            "issued_at": issued_at,
            "expires_at": expires_at,
            "trust_score": score,
            "trust_state": state
        }
        
        signature = self._sign_payload(payload)

        return CapabilityEnvelope(
            token_id=token_id,
            workload_id=workload_id,
            profile=profile,
            constraints=constraints,
            issued_at=issued_at,
            expires_at=expires_at,
            trust_score_at_issue=score,
            trust_state_at_issue=state,
            signature=signature
        )

    def _sign_payload(self, payload: dict) -> str:
        encoded = json.dumps(payload, sort_keys=True).encode("utf-8")
        h = hashlib.sha256()
        h.update(encoded)
        h.update(self.secret_seed.encode("utf-8"))
        return h.hexdigest()

    def verify_and_consume(self, envelope: CapabilityEnvelope, current_trust_context: dict) -> dict:
        """
        Vérification complète :
        1. Non-expiration (TTL)
        2. Intégrité signature
        3. CRL (Révocation ciblée)
        4. Anti-Replay (Consommation unique)
        5. Invalidation globale si hardware en QUARANTINE
        """
        now = time.time()

        # 1. TTL
        if now > envelope.expires_at:
            return {"valid": False, "reason": "TOKEN_EXPIRED"}

        # 2. Signature
        payload = {
            "token_id": envelope.token_id,
            "workload_id": envelope.workload_id,
            "profile": envelope.profile,
            "constraints": envelope.constraints,
            "issued_at": envelope.issued_at,
            "expires_at": envelope.expires_at,
            "trust_score": envelope.trust_score_at_issue,
            "trust_state": envelope.trust_state_at_issue
        }
        if self._sign_payload(payload) != envelope.signature:
            return {"valid": False, "reason": "TOKEN_SIGNATURE_TAMPERED"}

        # 3. CRL & Anti-Replay Check
        usable, rev_reason = self.revocation_registry.is_usable(envelope.token_id)
        if not usable:
            return {"valid": False, "reason": rev_reason}

        # 4. Invalidation Quarantaine Hardware
        current_state = current_trust_context.get("state", "QUARANTINE")
        if current_state == "QUARANTINE":
            return {"valid": False, "reason": "HARDWARE_ENTERED_QUARANTINE_AFTER_ISSUANCE"}

        current_score = current_trust_context.get("trust_score", 0)
        if current_score < envelope.trust_score_at_issue - 15:
            return {"valid": False, "reason": "TRUST_SCORE_DEGRADED_SIGNIFICANTLY_SINCE_ISSUANCE"}

        # 5. Marquage comme Consommé (Usage Unique Anti-Replay)
        self.revocation_registry.mark_consumed(envelope.token_id, envelope.expires_at)

        return {"valid": True, "reason": "CAPABILITY_ENVELOPE_VERIFIED_AND_CONSUMED"}
