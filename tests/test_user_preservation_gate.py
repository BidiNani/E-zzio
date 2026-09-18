"""
E-ZZIO Core V10.6 — Test Suite for User Preservation Gate (Zero Data Loss).
Teste la préservation des Scénarios A à F :
A — Fichier utilisateur préexistant
B — Patch minimal de configuration
C — Artifacts utilisateur référencés
D — Agents utilisateur intacts
E — Classification UNKNOWN -> PROTECTED
F — Blocage Delete Gate sur fichiers utilisateur
"""
import pytest

from core.authority.user_preservation import (
    FileOwnership,
    UserPreservationGate,
)


@pytest.fixture
def preservation_gate():
    return UserPreservationGate()


def test_scenario_a_user_file_preservation(preservation_gate):
    """Scenario A: Fichier utilisateur préexistant doit être conservé et inchangé."""
    path = "user_custom_script.py"
    content = b"print('User custom code')"

    preservation_gate.capture_baseline([path], {path: content})
    report = preservation_gate.verify_preservation({path: content})

    assert report.status == "PASS"
    assert report.user_data_loss == 0
    assert report.user_files_deleted == 0
    assert report.preexisting_changes_preserved is True


def test_scenario_b_minimal_config_patch(preservation_gate):
    """Scenario B: Modification minimale d'une configuration sans écraser les clés utilisateur."""
    user_config = {
        "custom_user_key": "user_val",
        "custom_provider_url": "http://localhost:11434",
        "timeout": 30,
    }
    patch = {"timeout": 60}  # Seul timeout est modifié

    result = preservation_gate.minimal_config_patch(user_config, patch)
    assert result["custom_user_key"] == "user_val"
    assert result["custom_provider_url"] == "http://localhost:11434"
    assert result["timeout"] == 60


def test_scenario_c_referenced_user_artifact(preservation_gate):
    """Scenario C: Un artifact utilisateur ne peut pas être supprimé par un cleanup."""
    artifact_path = "artifacts/user_report_v1.md"
    assert preservation_gate.classify_file(artifact_path) == FileOwnership.USER_OWNED
    assert preservation_gate.can_delete(artifact_path) is False  # Blocked


def test_scenario_d_user_agent_preservation(preservation_gate):
    """Scenario D: Agent utilisateur existant traité comme protégé."""
    agent_path = "user_agents/my_custom_agent.py"
    ownership = preservation_gate.classify_file(agent_path)
    assert ownership in (FileOwnership.USER_OWNED, FileOwnership.UNKNOWN)
    assert preservation_gate.can_delete(agent_path) is False


def test_scenario_e_unknown_file_classification(preservation_gate):
    """Scenario E: Fichier inconnu (UNKNOWN) traité par sécurité comme USER_OWNED (PROTECTED)."""
    unknown_path = "some_random_file.dat"
    ownership = preservation_gate.classify_file(unknown_path)
    assert ownership == FileOwnership.UNKNOWN
    assert preservation_gate.can_delete(unknown_path) is False


def test_scenario_f_delete_gate_blocking(preservation_gate):
    """Scenario F: Tentative de suppression d'un fichier utilisateur strictement bloquée."""
    user_file = "user_workflow.json"
    preservation_gate.capture_baseline([user_file], {user_file: b'{"name": "workflow"}'})

    # Simuler suppression
    report = preservation_gate.verify_preservation({}, deleted_paths=[user_file])
    assert report.status == "FAIL"
    assert report.user_files_deleted == 1
    assert report.user_data_loss == 1
