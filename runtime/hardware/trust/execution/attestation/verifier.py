import time
import uuid
import hashlib
import json
from runtime.hardware.trust.execution.attestation.models import ExecutionReceipt, AttestationVerdict
from runtime.hardware.trust.execution.attestation.collector import RuntimeObservationCollector
from runtime.hardware.trust.execution.ledger.hashchain import HashChainedLedger


class ExecutionAttestor:
    def __init__(self, ledger: HashChainedLedger, secret_seed: str = "EZZIO_ATTESTOR_ROOT_KEY"):
        self.ledger = ledger
        self.secret_seed = secret_seed

    def attest_and_record(
        self,
        execution_id: str,
        workload_id: str,
        capability_token_id: str,
        admission_grant_hash: str,
        contract_details: dict,
        model_identity: dict,
        target_pid: int,
        started_at: float,
    ) -> ExecutionReceipt:
        finished_at = time.time()
        violations = []

        # 1. Observation physique indépendante de l'OS
        observation = RuntimeObservationCollector.capture(target_pid)

        # 2. Analyse de conformité
        allowed_affinity = set(contract_details.get("allowed_affinity", []))
        actual_affinity = set(observation.actual_affinity_mask)

        if observation.is_alive and allowed_affinity and not actual_affinity.issubset(allowed_affinity):
            violations.append(f"AFFINITY_DRIFT_DETECTED: Allowed {list(allowed_affinity)}, Got {list(actual_affinity)}")

        max_ram_mb = contract_details.get("max_ram_mb", 999999)
        if observation.peak_ram_mb > max_ram_mb:
            violations.append(f"RESOURCE_VIOLATION_RAM: Limit {max_ram_mb}MB, Observed {observation.peak_ram_mb}MB")

        if not observation.is_alive:
            verdict = AttestationVerdict.ABORTED_CRASH.value
        elif violations:
            if any("AFFINITY" in v for v in violations):
                verdict = AttestationVerdict.VIOLATION_AFFINITY.value
            else:
                verdict = AttestationVerdict.VIOLATION_RESOURCE.value
        else:
            verdict = AttestationVerdict.COMPLIANT.value

        receipt_id = str(uuid.uuid4())
        contract_hash = hashlib.sha256(json.dumps(contract_details, sort_keys=True).encode("utf-8")).hexdigest()

        # Payload de signature exhaustif couvrant l'intégrité globale du reçu
        contract_payload = {
            "execution_id": execution_id,
            "workload_id": workload_id,
            "capability_token_id": capability_token_id,
            "admission_grant_hash": admission_grant_hash,
            "capability_contract_hash": contract_hash,
            "model_identity": model_identity,
            "contract": contract_details,
            "observation": {
                "pid": observation.pid,
                "actual_affinity_mask": observation.actual_affinity_mask,
                "active_threads": observation.active_threads,
                "peak_ram_mb": observation.peak_ram_mb,
                "is_alive": observation.is_alive,
            },
            "attestation_verdict": verdict,
            "violations": violations,
            "finished_at": finished_at,
        }
        signature = self._sign_receipt(contract_payload)

        raw_receipt = {
            "receipt_id": receipt_id,
            "execution_id": execution_id,
            "workload_id": workload_id,
            "capability_token_id": capability_token_id,
            "admission_grant_hash": admission_grant_hash,
            "capability_contract_hash": contract_hash,
            "model_identity": model_identity,
            "contract": contract_details,
            "observation": {
                "pid": observation.pid,
                "actual_affinity_mask": observation.actual_affinity_mask,
                "active_threads": observation.active_threads,
                "peak_ram_mb": observation.peak_ram_mb,
                "os_enforcement_verified": observation.os_enforcement_verified,
                "is_alive": observation.is_alive,
            },
            "attestation_verdict": verdict,
            "violations": violations,
            "timestamps": {"started_at": started_at, "finished_at": finished_at, "duration_sec": round(finished_at - started_at, 4)},
            "signature": signature,
        }

        self.ledger.append_receipt(raw_receipt)

        return ExecutionReceipt(
            sequence_id=0,
            previous_receipt_hash="",
            receipt_id=receipt_id,
            execution_id=execution_id,
            workload_id=workload_id,
            capability_token_id=capability_token_id,
            admission_grant_hash=admission_grant_hash,
            capability_contract_hash=contract_hash,
            model_identity=model_identity,
            contract=contract_details,
            observation=raw_receipt["observation"],
            attestation_verdict=verdict,
            violations=violations,
            timestamps=raw_receipt["timestamps"],
            signature=signature,
        )

    def _sign_receipt(self, payload: dict) -> str:
        encoded = json.dumps(payload, sort_keys=True).encode("utf-8")
        h = hashlib.sha256()
        h.update(encoded)
        h.update(self.secret_seed.encode("utf-8"))
        return h.hexdigest()

    @staticmethod
    def verify_receipt_signature(receipt: dict, secret_seed: str = "EZZIO_ATTESTOR_ROOT_KEY") -> bool:
        """Vérifie l'intégrité cryptographique globale du reçu (Tamper Detection)."""
        payload = {
            "execution_id": receipt.get("execution_id"),
            "workload_id": receipt.get("workload_id"),
            "capability_token_id": receipt.get("capability_token_id"),
            "admission_grant_hash": receipt.get("admission_grant_hash"),
            "capability_contract_hash": receipt.get("capability_contract_hash"),
            "model_identity": receipt.get("model_identity"),
            "contract": receipt.get("contract"),
            "observation": {
                "pid": receipt.get("observation", {}).get("pid"),
                "actual_affinity_mask": receipt.get("observation", {}).get("actual_affinity_mask"),
                "active_threads": receipt.get("observation", {}).get("active_threads"),
                "peak_ram_mb": receipt.get("observation", {}).get("peak_ram_mb"),
                "is_alive": receipt.get("observation", {}).get("is_alive"),
            },
            "attestation_verdict": receipt.get("attestation_verdict"),
            "violations": receipt.get("violations"),
            "finished_at": receipt.get("timestamps", {}).get("finished_at"),
        }
        encoded = json.dumps(payload, sort_keys=True).encode("utf-8")
        h = hashlib.sha256()
        h.update(encoded)
        h.update(secret_seed.encode("utf-8"))
        expected_sig = h.hexdigest()
        return expected_sig == receipt.get("signature")
