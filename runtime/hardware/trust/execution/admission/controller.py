import uuid
import time
import hashlib
import json
from runtime.hardware.trust.execution.admission.models import ExecutionRequest, AdmissionGrant
from runtime.hardware.trust.envelope.envelope import EnvelopeIssuer
from runtime.hardware.trust.policy.registry import TrustPolicyRegistry
from runtime.hardware.trust.models_governance.budget import ModelBudgetGovernor

class ExecutionAdmissionController:
    def __init__(self, envelope_issuer: EnvelopeIssuer, policy_registry: TrustPolicyRegistry, budget_governor: ModelBudgetGovernor, secret_seed: str = "EZZIO_ADMISSION_ROOT_KEY"):
        self.issuer = envelope_issuer
        self.policy_registry = policy_registry
        self.budget_governor = budget_governor
        self.secret_seed = secret_seed

    def admit(self, request: ExecutionRequest, current_trust_context: dict) -> AdmissionGrant:
        token = request.capability_token
        model = request.model_identity
        exec_id = str(uuid.uuid4())
        issued_at = time.time()

        # 1. Vérification du token d'enveloppe
        verify_result = self.issuer.verify_and_consume(token, current_trust_context)
        if not verify_result["valid"]:
            return AdmissionGrant(
                status="DENY",
                execution_id=exec_id,
                workload_id=request.workload_id,
                allowed_workers=0,
                allowed_profile=token.profile,
                granted_constraints={},
                issued_at=issued_at,
                capability_token_id=token.token_id,
                model_origin=model.model_id,
                reason=f"TOKEN_VERIFICATION_FAILED: {verify_result['reason']}",
                signature=""
            )

        # 2. Vérification du Trust Registry & Budget du Modèle émetteur
        requested_workers = token.constraints.get("max_workers", 4)
        budget_alloc = self.budget_governor.enforce_budget(model, requested_workers)
        
        if not budget_alloc.allowed:
            return AdmissionGrant(
                status="DENY",
                execution_id=exec_id,
                workload_id=request.workload_id,
                allowed_workers=0,
                allowed_profile=token.profile,
                granted_constraints={},
                issued_at=issued_at,
                capability_token_id=token.token_id,
                model_origin=model.model_id,
                reason=f"MODEL_REJECTED_BY_TRUST_REGISTRY: {budget_alloc.reason}",
                signature=""
            )

        # 3. Vérification de la politique globale hardware
        try:
            profile_rules = self.policy_registry.get_profile(token.profile)
        except Exception as e:
            return AdmissionGrant(
                status="DENY",
                execution_id=exec_id,
                workload_id=request.workload_id,
                allowed_workers=0,
                allowed_profile=token.profile,
                granted_constraints={},
                issued_at=issued_at,
                capability_token_id=token.token_id,
                model_origin=model.model_id,
                reason=f"POLICY_PROFILE_NOT_FOUND: {str(e)}",
                signature=""
            )

        # 4. Calcul final des workers (intersection budget modèle + limite policy hardware)
        max_workers_policy = profile_rules.get("constraints", {}).get("max_workers", 24)
        allowed_workers = min(budget_alloc.granted_workers, max_workers_policy)

        # 5. Scellement du grant
        payload = {
            "execution_id": exec_id,
            "workload_id": request.workload_id,
            "profile": token.profile,
            "allowed_workers": allowed_workers,
            "token_id": token.token_id,
            "model_id": model.model_id,
            "issued_at": issued_at
        }
        signature = self._sign_grant(payload)

        return AdmissionGrant(
            status="ALLOW",
            execution_id=exec_id,
            workload_id=request.workload_id,
            allowed_workers=allowed_workers,
            allowed_profile=token.profile,
            granted_constraints={"max_workers": allowed_workers, "max_ram_mb": budget_alloc.granted_ram_mb},
            issued_at=issued_at,
            capability_token_id=token.token_id,
            model_origin=model.model_id,
            reason="ADMISSION_GRANTED_WITH_MODEL_BUDGET",
            signature=signature
        )

    def _sign_grant(self, payload: dict) -> str:
        encoded = json.dumps(payload, sort_keys=True).encode("utf-8")
        h = hashlib.sha256()
        h.update(encoded)
        h.update(self.secret_seed.encode("utf-8"))
        return h.hexdigest()
