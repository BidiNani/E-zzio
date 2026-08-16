import json
import os
from runtime.hardware.evidence.ledger import HardwareEvidenceLedger
from runtime.hardware.evidence.validator import TopologyTrustValidator
from runtime.hardware.router.gate import AllocationIntegrityGate

class TopologyRouter:
    def __init__(self, validator: TopologyTrustValidator, dry_run: bool = True):
        self.validator = validator
        self.dry_run = dry_run
        self.policy_version = "6.12.2"
        
        self.policies = {
            "AI_INFERENCE": "CCD0",
            "BACKGROUND_SCAN": "CCD1",
            "STORAGE_IO": "BALANCED"
        }

    def _get_validated_snapshot(self):
        """Interface publique sécurisée pour récupérer le dernier état sans fuite d'implémentation privée."""
        if not self.validator.ledger.ledger_file.exists():
            return None
        try:
            with open(self.validator.ledger.ledger_file, "r", encoding="utf-8") as f:
                lines = [line.strip() for line in f if line.strip()]
                return json.loads(lines[-1]) if lines else None
        except (json.JSONDecodeError, OSError):
            return None

    def plan_workload(self, workload_type: str, current_probe: dict) -> dict:
        """Planification sous haute surveillance d'intégrité (Fail-Closed)."""
        
        # 1. Trust Gate (Validator)
        try:
            verdict = self.validator.validate_boot_state(current_probe)
        except Exception as e:
            return self._denied_verdict("TRUST_GATE_EXCEPTION", str(e))

        if not verdict.get("routing_allowed", False):
            return self._denied_verdict("TRUST_GATE_FAILED", verdict)

        # 2. Extraction sécurisée du snapshot
        latest = self._get_validated_snapshot()
        if not latest or not isinstance(latest, dict) or "hardware" not in latest:
            return self._denied_verdict("INVALID_SNAPSHOT_STRUCTURE")

        topo = latest["hardware"]
        cpu_info = topo.get("cpu", {})
        max_threads = cpu_info.get("logical", cpu_info.get("logical_threads", 0))
        
        if max_threads <= 0:
            return self._denied_verdict("INVALID_MAX_THREADS")

        clusters = topo.get("clusters", {})

        # 3. Allocation Integrity Gate (Vérification structurelle des clusters)
        if not AllocationIntegrityGate.validate_clusters(clusters, max_threads):
            return self._denied_verdict("ALLOCATION_INTEGRITY_GATE_FAILED")

        # 4. Résolution de politique (Fail-Closed sur work-load inconnu => BALANCED sécurisé)
        target_ccd = self.policies.get(workload_type, "BALANCED")
        allocation = self._resolve_allocation(clusters, target_ccd, max_threads)

        # 5. Gate finale sur l'allocation générée avant approbation
        if not AllocationIntegrityGate.validate_allocation(allocation, max_threads):
            return self._denied_verdict("GENERATED_ALLOCATION_CORRUPTED")

        return {
            "status": "APPROVED" if self.dry_run else "EXECUTED",
            "workload": workload_type,
            "target": target_ccd,
            "affinity_mask": allocation,
            "trust": {
                "chain_valid": verdict.get("chain_valid", False),
                "hardware_match": verdict.get("signature_match", False),
                "routing_allowed": verdict.get("routing_allowed", False)
            },
            "policy_version": self.policy_version,
            "mode": "DRY_RUN" if self.dry_run else "PRODUCTION"
        }

    def _denied_verdict(self, reason: str, details=None) -> dict:
        verdict_dict = {
            "status": "DENIED",
            "reason": reason,
            "policy_version": self.policy_version
        }
        if details is not None:
            verdict_dict["details"] = details
        return verdict_dict

    def _resolve_allocation(self, clusters: dict, target: str, max_threads: int) -> list:
        if target == "CCD0":
            return clusters.get("CCD0", [])
        elif target == "CCD1":
            return clusters.get("CCD1", [])
        else:  # BALANCED
            ccd0 = clusters.get("CCD0", [])
            ccd1 = clusters.get("CCD1", [])
            combined = ccd0 + ccd1
            # Élimination stricte des doublons tout en préservant l'ordre
            seen = set()
            unique_combined = []
            for cpu in combined:
                if cpu not in seen and 0 <= cpu < max_threads:
                    seen.add(cpu)
                    unique_combined.append(cpu)
            return unique_combined
