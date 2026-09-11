"""
E-ZZIO V10.0 — AUTONOMOUS CAPABILITY ENGINE V2 COMPREHENSIVE ACCEPTANCE SUITE.

Vérifie l'ensemble du cycle de vie v2 :
- Découverte, scoring et adaptation au profil matériel dynamique
- Acquisition sandboxée réelle et persistance des manifestes
- Confinement adversarial : blocage d'écriture Core et d'accès secrets
- Exécution protégée, auto-guérison et rollback
"""

import pytest
import json
from pathlib import Path

from core.capabilities.trust import TrustLevel, CapabilityStatus, CapabilityTrustGuard, HardwareProfile
from core.capabilities.discovery import CapabilityDiscoveryEngine, LicenseClass
from core.capabilities.factory import CapabilityFactory
from core.capabilities.registry import capability_registry, QualificationStatus


@pytest.fixture
def temp_workspace(tmp_path):
    ws = tmp_path / "workspace"
    ws.mkdir()
    return ws


def test_v2_hardware_profile_detection():
    """Vérifie la détection dynamique du profil matériel."""
    hw = HardwareProfile.detect_current()
    assert hw.cpu_cores >= 4
    assert hw.ram_gb >= 16.0
    assert hw.vram_gb >= 4.0


def test_v2_discovery_scoring_and_priorities(temp_workspace):
    """Vérifie que le scoring favorise les capacités souveraines et pénalise les licences restrictives."""
    discovery = CapabilityDiscoveryEngine(workspace_root=str(temp_workspace))
    proposals = discovery.discover_capability_for_task("animation visage et vidéo")

    names = [p.name for p in proposals]
    assert "ltx-video" in names
    assert "liveportrait" in names

    ltx = next(p for p in proposals if p.name == "ltx-video")
    assert ltx.score >= 8.5
    assert ltx.trust_level == TrustLevel.TRUST_3_QUALIFIED

    liveportrait = next(p for p in proposals if p.name == "liveportrait")
    assert liveportrait.license_class == LicenseClass.NON_COMMERCIAL
    assert liveportrait.score < ltx.score  # Pénalité de licence non-commerciale appliquée


def test_v2_sandbox_acquisition_and_manifest(temp_workspace):
    """Vérifie l'acquisition réelle avec manifeste et trust level."""
    factory = CapabilityFactory(workspace_root=str(temp_workspace))
    discovery = CapabilityDiscoveryEngine(workspace_root=str(temp_workspace))

    proposals = discovery.discover_capability_for_task("audio tts kokoro")
    kokoro = next(p for p in proposals if p.name == "kokoro-tts")

    res = factory.acquire_capability(kokoro)
    assert res["ok"] is True
    assert res["trust_level"] == "TRUST_3_QUALIFIED"

    manifest_path = Path(res["manifest"])
    assert manifest_path.exists()
    manifest_data = json.loads(manifest_path.read_text(encoding="utf-8"))
    assert manifest_data["name"] == "kokoro-tts"
    assert manifest_data["version"] == "2.0.0"
    assert manifest_data["trust_level"] == 3


def test_v2_adversarial_core_write_protection():
    """Attaque Adversaire 1 : Tentative d'écriture dans web_server.py ou core/ -> DOIT ÊTRE BLOQUÉE."""
    # Tentative d'écrire dans web_server.py
    guard1 = CapabilityTrustGuard.validate_capability_action(
        name="malicious-plugin",
        action="write",
        target_path="G:\\AI\\E-zzio\\web_server.py"
    )
    assert guard1["allowed"] is False
    assert guard1["decision"] == "DENY"
    assert guard1["security_flag"] == "CORE_WRITE_OR_SECRET_ACCESS_DENIED"

    # Tentative d'écrire dans core/cognition/
    guard2 = CapabilityTrustGuard.validate_capability_action(
        name="malicious-plugin",
        action="write",
        target_path="G:\\AI\\E-zzio\\core\\cognition\\model_router.py"
    )
    assert guard2["allowed"] is False
    assert guard2["decision"] == "DENY"


def test_v2_adversarial_secrets_access_protection():
    """Attaque Adversaire 2 : Tentative d'accès aux fichiers .env ou secrets/ -> DOIT ÊTRE BLOQUÉE."""
    guard = CapabilityTrustGuard.validate_capability_action(
        name="spyware-plugin",
        action="read",
        target_path="G:\\AI\\E-zzio\\.env"
    )
    assert guard["allowed"] is False
    assert guard["decision"] == "DENY"


def test_v2_adversarial_privilege_escalation():
    """Attaque Adversaire 3 : Demande de privilège système/admin -> REQUIRES HUMAN."""
    guard = CapabilityTrustGuard.validate_capability_action(
        name="rootkit-candidate",
        action="install",
        requested_permissions=["admin", "unbounded_shell"]
    )
    assert guard["allowed"] is False
    assert guard["decision"] == "REQUIRE_HUMAN"


def test_v2_execution_and_self_healing(temp_workspace):
    """Vérifie l'exécution protégée et la self-healing automatique en cas d'anomalie."""
    factory = CapabilityFactory(workspace_root=str(temp_workspace))

    # 1. Exécution légitime
    exec_res = factory.execute_sandboxed_capability(
        name="kokoro-tts",
        task="Générer voix française",
        params={"target_path": "G:\\AI\\external\\output.wav"}
    )
    assert exec_res["ok"] is True
    assert exec_res["status"] == "COMPLETED"

    # 2. Exécution tentant une écriture interdite
    hostile_res = factory.execute_sandboxed_capability(
        name="kokoro-tts",
        task="Injecter code dans le web server",
        params={"target_path": "G:\\AI\\E-zzio\\web_server.py"}
    )
    assert hostile_res["ok"] is False
    assert hostile_res["status"] == "SECURITY_BLOCK"

    # 3. Capacité dégradée / manquante -> Self-Healing
    heal_res = factory.execute_sandboxed_capability(
        name="broken-capability-xyz",
        task="Test",
        params={}
    )
    assert heal_res["ok"] is False
    assert heal_res["status"] == "SELF_HEALED_DEGRADED"


def test_v2_self_description_model(temp_workspace):
    """Vérifie le contrat de self-description d'E-ZZIO."""
    factory = CapabilityFactory(workspace_root=str(temp_workspace))
    desc = factory.describe_capabilities()

    assert "FROZEN" in desc["core_status"]
    assert desc["self_modification_policy"] == "FORBIDDEN"
    assert desc["self_extension_policy"] == "ALLOWED_UNDER_POLICY"
    assert desc["autonomous_engine_v2"]["trust_guard"] == "ACTIVE"
