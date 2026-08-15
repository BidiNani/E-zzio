"""
E-ZZIO V7.32 — Evolution Request Engine
Gère la création et le cycle de vie des demandes d'évolution.
"""
import json
import uuid
from pathlib import Path
from datetime import datetime, timezone
from core.authority.authority_policy import authority_policy_engine

ROOT_DIR = Path(__file__).resolve().parent.parent.parent
REQUESTS_DIR = ROOT_DIR / "runtime" / "evolution" / "requests"

class EvolutionRequestEngine:
    def __init__(self):
        REQUESTS_DIR.mkdir(parents=True, exist_ok=True)

    def create_request(self, evolution_type: str, target: str, reason: str, requested_by: str = "system") -> dict:
        request_id = f"EVOL-{uuid.uuid4().hex[:6].upper()}"
        
        policy_eval = authority_policy_engine.evaluate_target(target, evolution_type)
        
        status = "PENDING_VALIDATION" if policy_eval["requires_validation"] else "AUTO_APPROVED"
        if not policy_eval["allowed"]:
            status = "REJECTED"

        payload = {
            "request_id": request_id,
            "type": evolution_type,
            "target": target,
            "reason": reason,
            "requested_by": requested_by,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "policy_evaluation": policy_eval,
            "status": status
        }

        req_path = REQUESTS_DIR / f"{request_id}.json"
        req_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        return payload

evolution_request_engine = EvolutionRequestEngine()
