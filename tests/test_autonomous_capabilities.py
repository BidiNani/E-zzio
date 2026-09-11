"""
E-ZZIO V10.0 — AUTONOMOUS CAPABILITY ENGINE VALIDATION SUITE.
Vérifie la découverte, la qualification, le confinement sandbox,
l'enregistrement, le rollback et la non-auto-modification du Core.
"""

import pytest
import json
from pathlib import Path

from core.capabilities.discovery import CapabilityDiscoveryEngine, LicenseClass
from core.capabilities.factory import CapabilityFactory
from core.capabilities.registry import capability_registry, QualificationStatus


@pytest.fixture
def temp_workspace(tmp_path):
    ws = tmp_path / "workspace"
    ws.mkdir()
    return ws


def test_capability_discovery_and_hardware_fit(temp_workspace):
    """Vérifie que la découverte classe correctement les propositions selon le hardware et la licence."""
    discovery = CapabilityDiscoveryEngine(workspace_root=str(temp_workspace))

    # 1. Requête pour la vidéo
    proposals = discovery.discover_capability_for_task("générer de la vidéo locale")
    names = [p.name for p in proposals]
    assert "ltx-video" in names

    ltx = next(p for p in proposals if p.name == "ltx-video")
    assert ltx.hardware_fit is True
    assert ltx.commercial_allowed is True
    assert ltx.license_class == LicenseClass.PERMISSIVE

    # 2. Requête exigeant 16GB VRAM (Wan MoE)
    wan = next(p for p in proposals if p.name == "wan2.1-moe")
    assert wan.hardware_fit is False
    assert str(wan.status).upper() in ("REJECTED", "REJECTED_HARDWARE", "CAPABILITYSTATUS.REJECTED")


def test_capability_acquisition_and_sandbox_manifest(temp_workspace):
    """Vérifie l'installation sandboxée avec création du manifeste sans modifier le Core."""
    factory = CapabilityFactory(workspace_root=str(temp_workspace))
    discovery = CapabilityDiscoveryEngine(workspace_root=str(temp_workspace))

    proposals = discovery.discover_capability_for_task("audio tts")
    kokoro = next(p for p in proposals if p.name == "kokoro-tts")

    # Acquisition
    res = factory.acquire_capability(kokoro)
    assert res["ok"] is True
    assert res["status"] == "QUALIFIED"

    # Vérification du manifeste sandbox
    manifest_path = Path(res["manifest"])
    assert manifest_path.exists()
    manifest_data = json.loads(manifest_path.read_text(encoding="utf-8"))
    assert manifest_data["name"] == "kokoro-tts"
    assert manifest_data["healthy"] is True

    # Vérification de l'enregistrement dans le CapabilityRegistry
    qualif = capability_registry.get_qualification("kokoro-tts")
    assert qualif is not None
    assert qualif.status == QualificationStatus.QUALIFIED


def test_capability_rollback_and_self_healing(temp_workspace):
    """Vérifie la rétrogradation immédiate vers QUARANTINED en cas de dégradation."""
    factory = CapabilityFactory(workspace_root=str(temp_workspace))
    rollback_res = factory.rollback_capability("kokoro-tts")
    assert rollback_res["ok"] is True
    assert rollback_res["status"] == "QUARANTINED"

    qualif = capability_registry.get_qualification("kokoro-tts")
    assert qualif.status == QualificationStatus.QUARANTINED


def test_capability_self_description(temp_workspace):
    """Vérifie que la self-description distingue formellement Core Frozen et Capability Evolving."""
    factory = CapabilityFactory(workspace_root=str(temp_workspace))
    desc = factory.describe_capabilities()

    assert "FROZEN" in desc["core_status"]
    assert desc["self_modification_policy"] == "FORBIDDEN"
    assert desc["self_extension_policy"] == "ALLOWED_UNDER_POLICY"
    assert desc["registered_count"] > 0
