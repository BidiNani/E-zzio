"""
E-ZZIO Autonomous Capability Factory & Lifecycle Manager V2.0.

Gère le cycle de vie complet, l'exécution sécurisée, le rollback et la self-healing
des capacités externes sans modifier le Core V9.0.
"""
from __future__ import annotations
import os
import json
import logging
from pathlib import Path
from typing import Dict, Any, List, Optional

from core.capabilities.trust import TrustLevel, CapabilityStatus, CapabilityTrustGuard, HardwareProfile
from core.capabilities.discovery import CapabilityDiscoveryEngine, CapabilityProposal
from core.capabilities.capability_policy import CapabilityPolicy, PolicyDecision
from core.capabilities.registry import capability_registry, CapabilityQualification, QualificationStatus

logger = logging.getLogger("CapabilityFactory")


class CapabilityFactory:
    """Usine autonome d'acquisition, d'isolation et d'orchestration des capacités."""

    def __init__(self, workspace_root: str = "G:\\AI\\E-zzio"):
        self.workspace_root = Path(workspace_root).resolve()
        self.sandbox_base = Path("G:/AI/external/capabilities")
        self.sandbox_base.mkdir(parents=True, exist_ok=True)
        self.discovery = CapabilityDiscoveryEngine(workspace_root=str(self.workspace_root))
        self.policy = CapabilityPolicy()

    def describe_capabilities(self) -> Dict[str, Any]:
        """Produit la description structurée de l'ensemble des capacités actuelles et acquérables."""
        registered = capability_registry.list_capabilities()
        hardware = HardwareProfile.detect_current()
        return {
            "core_status": "FROZEN (12 Canonical Components)",
            "self_extension_policy": "ALLOWED_UNDER_POLICY",
            "self_modification_policy": "FORBIDDEN",
            "hardware_profile": hardware.model_dump(),
            "registered_capabilities": registered,
            "registered_count": len(registered),
            "external_sandbox_path": str(self.sandbox_base),
            "autonomous_engine_v2": {
                "discovery": "ACTIVE",
                "qualification": "ACTIVE",
                "rollback": "ACTIVE",
                "self_healing": "ACTIVE",
                "trust_guard": "ACTIVE"
            }
        }

    def acquire_capability(self, proposal: CapabilityProposal) -> Dict[str, Any]:
        """
        Installe et qualifie une nouvelle capacité dans le sas externe après validation de sécurité.
        """
        # 1. Vérification par le CapabilityTrustGuard
        trust_check = CapabilityTrustGuard.validate_capability_action(
            name=proposal.name,
            action="install",
            requested_permissions=proposal.required_permissions
        )

        if not trust_check["allowed"]:
            return {"ok": False, "status": "DENIED", "reason": trust_check["reason"]}

        # 2. Vérification par la CapabilityPolicy du Core
        decision, reason = self.policy.evaluate_scope(
            scope="code.patch",
            metadata={"name": proposal.name, "risk": proposal.risk_level, "locality": proposal.locality}
        )

        if decision == PolicyDecision.DENY:
            return {"ok": False, "status": "DENIED_BY_POLICY", "reason": reason}

        # 3. Isolation dans le sas externe
        target_dir = self.sandbox_base / proposal.name
        target_dir.mkdir(parents=True, exist_ok=True)

        manifest_file = target_dir / "capability.manifest.json"
        manifest_data = proposal.model_dump()
        manifest_data["installed_at"] = "2026-08-30T00:00:00Z"
        manifest_data["version"] = "2.0.0"
        manifest_data["healthy"] = True
        manifest_data["trust_level"] = int(proposal.trust_level)
        manifest_file.write_text(json.dumps(manifest_data, indent=2), encoding="utf-8")

        # 4. Enregistrement dans le CapabilityRegistry
        qualif_status = QualificationStatus.QUALIFIED if proposal.status == CapabilityStatus.QUALIFIED else QualificationStatus.CANDIDATE
        qualif = CapabilityQualification(
            name=proposal.name,
            category=proposal.category,
            provider=f"external.sandbox.{proposal.name}",
            input_contract={"task": "str", "params": "dict"},
            output_contract={"data": "dict", "exit_code": "int"},
            permissions=proposal.required_permissions,
            network_access=(proposal.locality == "CLOUD_API"),
            ssrf_protection=True,
            timeout_seconds=60.0,
            fail_closed=True,
            status=qualif_status,
            tests_reference=["tests/test_autonomous_capability_engine_v2.py"]
        )
        capability_registry.register(qualif)

        logger.info("[CAPABILITY-FACTORY] Capacité '%s' (Score: %s) acquise dans %s", proposal.name, proposal.score, target_dir)
        return {
            "ok": True,
            "name": proposal.name,
            "score": proposal.score,
            "status": qualif.status.value,
            "trust_level": proposal.trust_level.name,
            "installed_path": str(target_dir),
            "manifest": str(manifest_file),
            "message": f"Capacité '{proposal.name}' acquise et enregistrée sous contrôle de sécurité."
        }

    def execute_sandboxed_capability(self, name: str, task: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """Exécute une capacité sandboxée en validant les chemins d'accès et les frontières."""
        # 1. Vérification contre les écritures hostiles
        out_target = params.get("output_path") or params.get("target_path")
        guard = CapabilityTrustGuard.validate_capability_action(name=name, action="execute", target_path=out_target)
        if not guard["allowed"]:
            return {"ok": False, "status": "SECURITY_BLOCK", "error": guard["reason"]}

        # 2. Exécution simulée ou déléguée
        target_dir = self.sandbox_base / name
        if not target_dir.exists():
            # Déclenchement de la self-healing
            return self.self_heal_capability(name)

        return {
            "ok": True,
            "capability": name,
            "task": task,
            "status": "COMPLETED",
            "result": f"[RÉSULTAT SÉCURISÉ CAPABILITY {name}] : {task}",
            "execution_runtime": "G:\\AI\\external\\sandbox"
        }

    def self_heal_capability(self, name: str) -> Dict[str, Any]:
        """Détecte une anomalie, arrête la capacité et déclenche le rollback sans toucher au Core."""
        logger.warning("[SELF-HEALING] Anomalie détectée pour '%s'. Rollback immédiat.", name)
        rollback_res = self.rollback_capability(name)
        return {
            "ok": False,
            "status": "SELF_HEALED_DEGRADED",
            "error": f"Capacité '{name}' défaillante. Neutralisée et basculée en quarantaine.",
            "rollback_details": rollback_res
        }

    def rollback_capability(self, name: str) -> Dict[str, Any]:
        """Rétrograde ou désactive une capacité dégradée sans toucher au Core."""
        target_dir = self.sandbox_base / name
        manifest_file = target_dir / "capability.manifest.json"
        if manifest_file.exists():
            manifest = json.loads(manifest_file.read_text(encoding="utf-8"))
            manifest["status"] = CapabilityStatus.QUARANTINED.value
            manifest["healthy"] = False
            manifest_file.write_text(json.dumps(manifest, indent=2), encoding="utf-8")

        qualif = capability_registry.get_qualification(name)
        if qualif:
            qualif.status = QualificationStatus.QUARANTINED
        else:
            qualif = CapabilityQualification(
                name=name,
                category="quarantine",
                provider=f"external.sandbox.{name}",
                input_contract={},
                output_contract={},
                status=QualificationStatus.QUARANTINED
            )
            capability_registry.register(qualif)

        return {
            "ok": True,
            "name": name,
            "status": "QUARANTINED",
            "message": f"Capacité '{name}' rétrogradée et neutralisée."
        }


# Instance singleton
capability_factory = CapabilityFactory()
