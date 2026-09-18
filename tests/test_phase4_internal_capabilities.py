"""
Phase 4 Test Suite — Validation des capacités internes (Test Loop, Rollback, Traçabilité, Routage Modèle).
"""

import pytest

from core.agent.coding_agent_loop import CodingAgentHarness
from core.agent.patch_engine import PatchEngine
from core.capabilities.capability_policy import CapabilityPolicy, PolicyDecision


def test_phase4_task_complexity_routing():
    """Vérifie le routage modèle par niveau de difficulté."""
    harness = CodingAgentHarness()

    # Simple recherche -> Modèle Lite
    assert harness.evaluate_task_complexity("cherche où est définie la fonction compute") == "gemini-3.5-flash-lite"

    # Développement standard / Patch -> Modèle Flash
    assert harness.evaluate_task_complexity("corrige le bug dans math_utils") == "gemini-3.7-flash"

    # Architecture lourde / AST -> Modèle Pro
    assert harness.evaluate_task_complexity("refactor et restructure l'architecture AST") == "gemini-3.1-pro"


def test_phase4_snapshot_audit_log(tmp_path):
    """Vérifie que chaque modification est tracée et snapshotée."""
    workspace = tmp_path / "traced_workspace"
    workspace.mkdir()
    f = workspace / "data.py"
    f.write_text("VALUE = 1\n", encoding="utf-8")

    patcher = PatchEngine(workspace_root=str(workspace))
    patcher.apply_search_replace("data.py", "VALUE = 1", "VALUE = 2")

    # Vérification de l'existence du snapshot
    snapshots = list((workspace / "state" / "snapshots").glob("*.bak"))
    assert len(snapshots) >= 1


def test_phase4_human_escalation_criteria():
    """Vérifie les critères stricts d'escalade REQUIRE_HUMAN."""
    policy = CapabilityPolicy()

    # Écriture externe / mutation SaaS -> REQUIRE_HUMAN
    dec1, _ = policy.evaluate_scope("gmail.send", {"target": "boss@example.com"})
    assert dec1 == PolicyDecision.REQUIRE_HUMAN

    # Push de code distant -> REQUIRE_HUMAN
    dec2, _ = policy.evaluate_scope("github.push", {"branch": "main"})
    assert dec2 == PolicyDecision.REQUIRE_HUMAN
