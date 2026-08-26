from runtime.hardware.trust.policy.registry import TrustPolicyRegistry
from runtime.hardware.trust.ledger.policy_ledger import PolicyAuditLedger


class PolicyDecisionPoint:
    def __init__(self, registry: TrustPolicyRegistry, audit_ledger: PolicyAuditLedger):
        self.registry = registry
        self.ledger = audit_ledger

    def evaluate(self, trust_context: dict, request) -> dict:
        """
        Évalue la permission d'exécution en croisant l'état du Trust Engine
        et le profil de criticité du Workload.
        """
        profile_name = request.profile
        try:
            profile_rules = self.registry.get_profile(profile_name)
        except ValueError as e:
            return {"decision": "DENY", "reason": str(e)}

        min_score = profile_rules.get("minimum_score", 0)
        allowed_states = profile_rules.get("allowed_states", [])
        constraints = profile_rules.get("constraints", {})

        current_score = trust_context.get("trust_score", 0)
        current_state = trust_context.get("state", "QUARANTINE")

        # 1. Vérification du Score Minimum
        if current_score < min_score:
            result = {"decision": "DENY", "reason": f"TRUST_SCORE_TOO_LOW_FOR_PROFILE (Current: {current_score}, Required: {min_score})"}
        # 2. Vérification de l'État de la Machine à États
        elif current_state not in allowed_states:
            result = {"decision": "DENY", "reason": f"{profile_name}_REQUIRES_ONE_OF_STATES_{allowed_states}_GOT_{current_state}"}
        else:
            result = {
                "decision": "ALLOW",
                "profile": profile_name,
                "constraints": constraints,
                "reason": f"TRUST_SCORE_AND_STATE_ACCEPTABLE_FOR_{profile_name}",
            }

        # 3. Traçabilité obligatoire dans le Ledger d'audit
        req_dict = {"workload_id": request.workload_id, "profile": request.profile}
        self.ledger.log_decision(trust_context, req_dict, result, self.registry.get_version())

        return result
