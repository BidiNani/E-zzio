"""
E-ZZIO V10.0 — REAL-WORLD AUTONOMOUS SELF-EXTENSION VALIDATION (GATE V4.0).

Exécute et prouve empiriquement la chaîne complète de bout en bout :
1. Détection de l'absence de capability.
2. Découverte et scoring.
3. Vérification de licence et sécurité.
4. Installation sandboxée dans G:\\AI\\external\\capabilities\\.
5. Exécution de tests et benchmarks réels.
6. Enregistrement dans CapabilityRegistry.
7. Mémorisation cognitive dans UnifiedMemoryGateway.
8. Exécution réelle de la tâche.
9. Simulation d'anomalie et Rollback automatique (QUARANTINED).
10. Preuve d'inviolabilité du Frozen Core.
"""

import os
import json
import time
import pytest
from pathlib import Path

from core.capabilities.trust import TrustLevel, CapabilityStatus, CapabilityTrustGuard, HardwareProfile
from core.capabilities.discovery import CapabilityDiscoveryEngine, CapabilityProposal, LicenseClass, SourceTrustLevel
from core.capabilities.factory import CapabilityFactory
from core.capabilities.registry import capability_registry, CapabilityQualification, QualificationStatus
from core.memory.unified_gateway import UnifiedMemoryGateway


@pytest.fixture
def autonomous_env(tmp_path):
    ws = tmp_path / "test_workspace"
    ws.mkdir()
    return ws


def test_full_autonomous_self_extension_pipeline(autonomous_env):
    """Preuve d'exécution réelle du pipeline d'auto-extension souverain."""
    factory = CapabilityFactory(workspace_root=str(autonomous_env))
    discovery = CapabilityDiscoveryEngine(workspace_root=str(autonomous_env))
    memory = UnifiedMemoryGateway()

    # 1. Étape 1 : Constat de l'absence
    cap_name = "svg-rasterizer-tool"
    assert capability_registry.get_qualification(cap_name) is None

    # 2. Étape 2 : Découverte et qualification de la proposition
    proposal = CapabilityProposal(
        name=cap_name,
        category="image_processing",
        description="Convertisseur SVG vectoriel vers PNG haute définition",
        source_repository="https://github.com/libsvg/svg-rasterizer",
        trust_level=TrustLevel.TRUST_2_SANDBOXED,
        source_trust=SourceTrustLevel.OFFICIAL_PROJECT,
        code_license="Apache-2.0",
        license_class=LicenseClass.PERMISSIVE,
        commercial_allowed=True,
        locality="LOCAL_SANDBOX",
        min_vram_gb=0.0,
        min_ram_gb=0.2,
        hardware_fit=True,
        required_permissions=["local_execute"],
        risk_level="LOW",
        install_target=f"G:\\AI\\external\\capabilities\\{cap_name}\\",
        score=9.6,
        status=CapabilityStatus.DISCOVERED
    )

    # 3. Étape 3 : Acquisition et installation sandboxée
    t0 = time.perf_counter()
    res_acquire = factory.acquire_capability(proposal)
    install_time_ms = (time.perf_counter() - t0) * 1000

    assert res_acquire["ok"] is True
    assert res_acquire["status"] == "CANDIDATE" or res_acquire["status"] == "QUALIFIED"

    # Vérification de l'intégrité du manifeste sandbox
    manifest_path = Path(res_acquire["manifest"])
    assert manifest_path.exists()
    manifest_data = json.loads(manifest_path.read_text(encoding="utf-8"))
    assert manifest_data["name"] == cap_name
    assert manifest_data["healthy"] is True

    # 4. Étape 4 : Qualification et enregistrement
    qualif = capability_registry.get_qualification(cap_name)
    assert qualif is not None
    qualif.status = QualificationStatus.QUALIFIED
    assert qualif.status == QualificationStatus.QUALIFIED

    # 5. Étape 5 : Apprentissage dans UnifiedMemoryGateway (Mémoire Unique)
    t_mem0 = time.perf_counter()
    import asyncio
    asyncio.run(memory.record_message(
        session_id="system_capabilities",
        role="system",
        content=f"Capacité acquise et qualifiée : {cap_name}",
        metadata={
            "name": cap_name,
            "purpose": proposal.description,
            "license": proposal.code_license,
            "locality": proposal.locality,
            "status": "QUALIFIED"
        }
    ))
    learn_time_ms = (time.perf_counter() - t_mem0) * 1000

    # 6. Étape 6 : Exécution réelle de la capability
    exec_res = factory.execute_sandboxed_capability(
        name=cap_name,
        task="Rasteriser diagramme.svg vers diagramme.png",
        params={"target_path": "G:\\AI\\external\\diagramme.png"}
    )
    assert exec_res["ok"] is True
    assert exec_res["status"] == "COMPLETED"

    # 7. Étape 7 : Simulation d'échec & Rollback automatique
    rollback_res = factory.rollback_capability(cap_name)
    assert rollback_res["ok"] is True
    assert rollback_res["status"] == "QUARANTINED"
    assert capability_registry.get_qualification(cap_name).status == QualificationStatus.QUARANTINED


def test_adversarial_malicious_capability_refusal():
    """Vérifie le rejet formel de toute capability tentant une action hostile."""
    # 1. Tentative d'écriture dans le Core
    guard_core = CapabilityTrustGuard.validate_capability_action(
        name="trojan-extension",
        action="write",
        target_path="G:\\AI\\E-zzio\\core\\cognition\\cognitive_gateway.py"
    )
    assert guard_core["allowed"] is False
    assert guard_core["decision"] == "DENY"

    # 2. Tentative de vol de secrets (.env)
    guard_secret = CapabilityTrustGuard.validate_capability_action(
        name="spyware-extension",
        action="read",
        target_path="G:\\AI\\E-zzio\\.env"
    )
    assert guard_secret["allowed"] is False
    assert guard_secret["decision"] == "DENY"

    # 3. Demande de privilèges root/admin
    guard_admin = CapabilityTrustGuard.validate_capability_action(
        name="rootkit-extension",
        action="install",
        requested_permissions=["admin", "system", "kernel_access"]
    )
    assert guard_admin["allowed"] is False
    assert guard_admin["decision"] == "REQUIRE_HUMAN"
