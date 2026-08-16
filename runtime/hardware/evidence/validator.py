import json
import time
from runtime.hardware.evidence.ledger import HardwareEvidenceLedger
from runtime.experiments.v611_topology.discovery_hardened import HardenedDiscovery

class TopologyTrustValidator:
    def __init__(self, ledger: HardwareEvidenceLedger):
        self.ledger = ledger

    def _get_hardware_only(self, probe: dict) -> dict:
        clean = probe.copy()
        clean.pop("timestamp", None)
        return clean

    def validate_boot_state(self, current_hw_probe: dict) -> dict:
        """Produit un verdict de confiance rigoureux."""
        
        # 1. Vérifier l'intégrité globale de la chaîne (Ledger)
        chain_valid = self.ledger.verify_chain()
        latest = self._get_latest_snapshot()
        
        if not chain_valid or latest is None or "hardware" not in latest:
            return {
                "hardware_trusted": False,
                "signature_match": False,
                "chain_valid": chain_valid,
                "routing_allowed": False,
                "timestamp": time.time()
            }
        
        # 2. Comparaison structurelle du matériel (nettoyé des timestamps)
        current_hw_clean = self._get_hardware_only(current_hw_probe)
        trusted_hw_clean = self._get_hardware_only(latest["hardware"])
        
        hardware_match = (current_hw_clean == trusted_hw_clean)
        
        verdict = {
            "hardware_trusted": chain_valid and hardware_match,
            "signature_match": hardware_match,
            "chain_valid": chain_valid,
            "routing_allowed": chain_valid and hardware_match,
            "timestamp": time.time()
        }
        return verdict

    def _get_latest_snapshot(self):
        if not self.ledger.ledger_file.exists(): return None
        try:
            with open(self.ledger.ledger_file, "r", encoding="utf-8") as f:
                lines = [line.strip() for line in f if line.strip()]
                return json.loads(lines[-1]) if lines else None
        except (json.JSONDecodeError, OSError):
            return None
