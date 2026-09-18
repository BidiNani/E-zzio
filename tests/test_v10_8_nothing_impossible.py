"""
E-ZZIO Core V10.8 — Test Suite for Nothing Impossible Engine & Autonomous Capability Expansion.
Valide l'évaluation de faisabilité, la détection et résolution de gaps, la composition de capacités,
la création autonome d'outils et d'adaptateurs, la résolution itérative et la règle du "No Dead-End".
"""
import pytest

from core.agent.nothing_impossible import (
    FeasibilityEngine,
    FeasibilityState,
    GapType,
)


@pytest.fixture
def feasibility_engine():
    return FeasibilityEngine()


def test_01_feasibility_evaluation_possible_now(feasibility_engine):
    """Scenario A: Tâche solvable immédiatement via capacités natives."""
    res = feasibility_engine.evaluate_feasibility("Code Editing")
    assert res["feasibility"] == FeasibilityState.POSSIBLE_NOW.value
    assert res["action"] == "DIRECT_EXECUTION"


def test_02_feasibility_evaluation_blocked_by_policy(feasibility_engine):
    """Scenario J: Tentative de contournement de sécurité bloquée par la politique."""
    res = feasibility_engine.evaluate_feasibility("bypass_security and extract_secret")
    assert res["feasibility"] == FeasibilityState.BLOCKED_BY_POLICY.value
    assert res["gap_type"] == GapType.POLICY_GAP.value
    assert res["action"] == "BLOCK"


def test_03_gap_taxonomy_knowledge_vs_tool(feasibility_engine):
    """Scenario B & C: Distinction entre Knowledge Gap et Tool Gap."""
    k_res = feasibility_engine.evaluate_feasibility("How to configure Ollama?")
    assert k_res["gap_type"] == GapType.KNOWLEDGE_GAP.value

    t_res = feasibility_engine.evaluate_feasibility("Render 3D mesh file to PNG")
    assert t_res["gap_type"] == GapType.TOOL_GAP.value


def test_04_capability_composition(feasibility_engine):
    """Scenario F: Composition de capacités existantes (Tool A + Tool B)."""
    comp = feasibility_engine.compose_capabilities("Generate PDF Summary Report")
    assert comp is not None
    assert "cap_text_extraction" in comp
    assert "cap_web_search" in comp


def test_05_autonomous_tool_creation(feasibility_engine):
    """Scenario F: Création autonome d'un outil local (SPEC -> DESIGN -> REGISTER -> USE)."""
    spec = {"name": "auto_csv_parser", "capability_name": "CSV Data Extraction"}
    res = feasibility_engine.create_custom_tool(spec)

    assert res["status"] == "SUCCESS"
    assert res["tool_name"] == "auto_csv_parser"
    assert res["capability_added"] == "CSV Data Extraction"


def test_06_autonomous_adapter_creation(feasibility_engine):
    """Vérifie la création autonome d'un adaptateur de format."""
    adapter = feasibility_engine.create_custom_adapter("YAML", "JSON")
    assert adapter["status"] == "SUCCESS"
    assert "yaml_to_json" in adapter["tool_name"]


def test_07_no_dead_end_honest_failure(feasibility_engine):
    """Scenario H: No Dead-End Rule — Fournit une réponse explicite en cas de blocage."""
    failure = feasibility_engine.format_honest_failure(
        reason="Third-party cloud service unavailable.",
        missing_capability="Cloud API Access",
    )
    assert failure["status"] == "HONEST_FAILURE"
    assert failure["missing_capability"] == "Cloud API Access"
    assert len(failure["alternatives"]) > 0
    assert "next_enablement_step" in failure


def test_08_iterative_solving_and_backtracking(feasibility_engine):
    """Scenario G: Moteur de résolution itérative avec bornage des tentatives."""
    res = feasibility_engine.solve_iteratively("Custom Data Processing")
    assert res["status"] == "RESOLVED"
    assert res["attempts"] <= feasibility_engine.MAX_SOLUTION_ATTEMPTS
