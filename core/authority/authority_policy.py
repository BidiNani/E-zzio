"""
E-ZZIO V7.32 — Authority Policy Engine
Définit les domaines protégés, les exigences de validation et les autorisations automatiques.
"""

import json
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent.parent
POLICY_FILE = ROOT_DIR / "runtime" / "evolution" / "authority_policy.json"

DEFAULT_POLICY = {
    "protected_domains": ["identity", "constitution", "security"],
    "require_validation": ["kernel", "memory", "skills"],
    "automatic_allowed": ["cache", "telemetry", "optimization"],
}


class AuthorityPolicyEngine:
    def __init__(self):
        POLICY_FILE.parent.mkdir(parents=True, exist_ok=True)
        if not POLICY_FILE.exists():
            POLICY_FILE.write_text(json.dumps(DEFAULT_POLICY, indent=2), encoding="utf-8")
        self.policy = json.loads(POLICY_FILE.read_text(encoding="utf-8"))

    def evaluate_target(self, target: str, evolution_type: str) -> dict:
        if target in self.policy.get("protected_domains", []):
            return {"allowed": False, "requires_validation": True, "reason": "PROTECTED_DOMAIN_MUTATION_FORBIDDEN"}
        if target in self.policy.get("require_validation", []):
            return {"allowed": True, "requires_validation": True, "reason": "VALIDATION_REQUIRED_BY_MENTOR"}
        if target in self.policy.get("automatic_allowed", []):
            return {"allowed": True, "requires_validation": False, "reason": "AUTOMATIC_OPTIMIZATION_ALLOWED"}
        return {"allowed": False, "requires_validation": True, "reason": "UNKNOWN_DOMAIN_REJECTED_BY_DEFAULT"}


authority_policy_engine = AuthorityPolicyEngine()
