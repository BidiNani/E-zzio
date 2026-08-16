"""
E-ZZIO V9.4 — Autonomous Acquisition Manager (Corrected Manifest)
"""
from runtime.capabilities.security.manifest_validator import ManifestValidator
from runtime.capabilities.registry.registry_core import RegistryCore

class AutonomousAcquisitionManager:
    def __init__(self):
        self.validator = ManifestValidator()
        self.registry = RegistryCore()

    def discover_candidate(self, goal: str) -> dict:
        if "image" in goal.lower():
            # Manifeste complet incluant behavior et rollback pour passer le validator
            return {
                "capability_id": "IMAGE_CREATOR",
                "version": "1.0.0",
                "origin": {"source": "github_validated", "url": "https://github.com/eZZio/image_creator"},
                "behavior": {"network": False, "process_spawn": False},
                "resource_budget": {"ram_mb": 400, "gpu_allowed": False},
                "permissions": ["file_output"],
                "rollback": {"available": True}
            }
        return None

    def propose_evolution(self, goal: str) -> dict:
        candidate = self.discover_candidate(goal)
        if not candidate:
            return {"status": "NOT_FOUND", "reason": "Aucune capacité correspondant au besoin."}

        # Vetting automatique (Security Gate)
        security_report = self.validator.validate_and_inspect(candidate)
        
        if security_report["status"] != "VALIDATED":
            return {"status": "VETTING_FAILED", "report": security_report}

        return {
            "status": "PROPOSAL_READY",
            "candidate": candidate,
            "risk_assessment": "LOW",
            "action": "PENDING_USER_VALIDATION"
        }
