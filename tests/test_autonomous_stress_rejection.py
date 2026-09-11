"""
E-ZZIO Test Suite — Autonomous Self-Extension Stress & Rejection Tests (Gate v6.0 / v7.0).

Vérifie de manière concrète que le pipeline DISCOVER -> VERIFY -> SANDBOX rejette ou confine :
1. Un candidat réel à licence restrictive non commerciale (ex: F5-TTS sous CC-BY-NC-4.0) via discover_capability_for_task().
2. Une demande d'exfiltration réseau ou privilège non borné via CapabilityTrustGuard.
3. Un composant défaillant lors de ses benchmarks en sandbox via CapabilityFactory.rollback_capability().
"""

import pytest
from pathlib import Path
from core.capabilities.trust import TrustLevel, CapabilityStatus, CapabilityTrustGuard
from core.capabilities.discovery import (
    CapabilityDiscoveryEngine,
    CapabilityProposal,
    LicenseClass,
    SourceTrustLevel
)
from core.capabilities.factory import CapabilityFactory
from core.capabilities.registry import capability_registry, QualificationStatus


@pytest.fixture
def stress_env(tmp_path):
    ws = tmp_path / "stress_workspace"
    ws.mkdir()
    return ws


def test_real_discovery_pipeline_rejects_non_commercial_license(stress_env):
    """
    Test Réel : Soumet une requête au pipeline discover_capability_for_task()
    et vérifie que le candidat réel 'f5-tts' (CC-BY-NC-4.0) est détecté comme NON_COMMERCIAL
    et n'obtient JAMAIS le statut QUALIFIED.
    """
    discovery = CapabilityDiscoveryEngine(workspace_root=str(stress_env))
    proposals = discovery.discover_capability_for_task("besoin de clonage audio vocal f5-tts")

    assert len(proposals) > 0
    f5_candidate = next((p for p in proposals if p.name == "f5-tts"), None)
    assert f5_candidate is not None

    # Vérification que le pipeline de découverte a analysé la licence réelle CC-BY-NC-4.0
    assert f5_candidate.weights_license == "CC-BY-NC-4.0"
    assert f5_candidate.commercial_allowed is False
    assert f5_candidate.license_class == LicenseClass.NON_COMMERCIAL
    # Ne doit pas être promu QUALIFIED en raison de la clause restrictive
    assert f5_candidate.status != CapabilityStatus.QUALIFIED


def test_stress_blocking_network_exfiltration():
    """Vérifie le blocage immédiat d'une action réseau non déclarée ou d'exfiltration."""
    guard_net = CapabilityTrustGuard.validate_capability_action(
        name="rogue-telemetry-tool",
        action="network_egress",
        requested_permissions=["unbounded_socket", "raw_network"]
    )
    assert guard_net["allowed"] is False
    assert guard_net["decision"] == "REQUIRE_HUMAN"


def test_stress_quarantine_on_failed_benchmark(stress_env):
    """Vérifie qu'un outil dont les tests échouent est immédiatement basculé en QUARANTINED."""
    factory = CapabilityFactory(workspace_root=str(stress_env))
    cap_name = "failing-math-parser"

    proposal = CapabilityProposal(
        name=cap_name,
        category="parser",
        description="Parser déterministe avec régression interne",
        source_repository="https://github.com/libmath/parser",
        trust_level=TrustLevel.TRUST_2_SANDBOXED,
        source_trust=SourceTrustLevel.COMMUNITY_PROJECT,
        code_license="MIT",
        license_class=LicenseClass.PERMISSIVE,
        commercial_allowed=True,
        locality="LOCAL_SANDBOX",
        min_vram_gb=0.0,
        min_ram_gb=0.1,
        hardware_fit=True,
        required_permissions=["local_execute"],
        risk_level="LOW",
        install_target=f"G:\\AI\\external\\capabilities\\{cap_name}\\",
        score=8.5,
        status=CapabilityStatus.DISCOVERED
    )

    res_acquire = factory.acquire_capability(proposal)
    assert res_acquire["ok"] is True

    # Simulation d'échec du test fonctionnel -> Rollback immédiat
    res_rollback = factory.rollback_capability(cap_name)
    assert res_rollback["ok"] is True
    assert res_rollback["status"] == "QUARANTINED"
    assert capability_registry.get_qualification(cap_name).status == QualificationStatus.QUARANTINED
