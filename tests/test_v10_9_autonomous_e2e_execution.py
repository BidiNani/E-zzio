"""
E-ZZIO Core V10.9 — Test Suite for Autonomous End-to-End Execution Engine.
Valide le contrat de mission, l'exécution DAG, les checkpoints/reprise, la vérification déterministe,
la récupération autonome (Self-Healing), l'adaptabilité du replanning et le scénario E2E complet.
"""
import pytest

from core.agent.autonomous_e2e_engine import (
    AutonomousE2EEngine,
    MissionState,
    ResultVerificationEngine,
)


@pytest.fixture
def e2e_engine():
    return AutonomousE2EEngine()


def test_01_mission_contract_creation(e2e_engine):
    """Vérifie la création et l'initialisation du contrat de mission autonome."""
    contract = e2e_engine.create_mission_contract(
        objective="Analyze Codebase and Build Performance Report",
        user_intent="Autonomous End-to-End Execution",
        execution_budget=150.0,
        risk_level="R1",
    )
    assert contract.mission_id.startswith("mission_")
    assert contract.current_state == MissionState.RECEIVED
    assert contract.execution_budget == 150.0
    assert contract.approval_requirements is False


def test_02_dag_plan_validation_and_cycle_detection(e2e_engine):
    """Vérifie la validation du plan DAG et la détection autonome de cycle."""
    contract = e2e_engine.create_mission_contract("DAG Validation", "Testing DAG")

    # Plan valide
    plan_nodes = [
        {"node_id": "node_1", "type": "RESEARCH"},
        {"node_id": "node_2", "type": "CODE"},
    ]
    deps = {"node_2": ["node_1"]}
    valid = e2e_engine.build_execution_plan(contract.mission_id, plan_nodes, deps)
    assert valid is True
    assert contract.current_state == MissionState.PREPARING

    # Plan avec cycle (node_1 -> node_2 -> node_1)
    cycle_contract = e2e_engine.create_mission_contract("Cycle Test", "Cycle Test")
    cycle_nodes = [
        {"node_id": "n1"},
        {"node_id": "n2"},
    ]
    cycle_deps = {"n1": ["n2"], "n2": ["n1"]}
    invalid = e2e_engine.build_execution_plan(cycle_contract.mission_id, cycle_nodes, cycle_deps)
    assert invalid is False
    assert cycle_contract.current_state == MissionState.FAILED
    assert cycle_contract.completion_state == "DAG_CYCLE_DETECTED"


def test_03_checkpoint_and_resume_lifecycle(e2e_engine):
    """Vérifie la sauvegarde de points de restauration (Checkpoints) et la reprise après interruption."""
    contract = e2e_engine.create_mission_contract("Checkpoint Test", "Testing Checkpoints")
    cp = e2e_engine.create_checkpoint(contract.mission_id, step_index=1, completed_nodes=["node_1"], pending_nodes=["node_2"])

    assert cp.step_index == 1
    assert cp.completed_nodes == ["node_1"]

    resumed = e2e_engine.resume_from_checkpoint(contract.mission_id)
    assert resumed is not None
    assert resumed.checkpoint_id == cp.checkpoint_id
    assert contract.current_state == MissionState.EXECUTING


def test_04_result_verification_layer():
    """Vérifie la couche déterministe de vérification de résultat selon le type de tâche."""
    verifier = ResultVerificationEngine()

    # CODE Verification
    ok_code, _ = verifier.verify_node_output("CODE", "def test(): return True")
    assert ok_code is True

    err_code, msg_code = verifier.verify_node_output("CODE", "SyntaxError: invalid syntax")
    assert err_code is False
    assert "syntax" in msg_code

    # FILE Verification
    ok_file, _ = verifier.verify_node_output("FILE", {"exists": True, "size": 1024})
    assert ok_file is True

    err_file, _ = verifier.verify_node_output("FILE", {"exists": False})
    assert err_file is False


def test_05_approval_gate_blocking_high_risk(e2e_engine):
    """Vérifie que les missions à haut risque (R3/R4) requièrent l'accord utilisateur (HITL)."""
    contract = e2e_engine.create_mission_contract(
        objective="Deploy Production Patch",
        user_intent="High Risk Deployment",
        risk_level="R3",
    )
    plan_nodes = [{"node_id": "node_deploy", "type": "CODE"}]
    e2e_engine.build_execution_plan(contract.mission_id, plan_nodes, {})

    res = e2e_engine.execute_mission_e2e(contract.mission_id)
    assert res["status"] == "BLOCKED_REQUIRES_APPROVAL"
    assert contract.current_state == MissionState.BLOCKED


def test_06_realistic_end_to_end_integration_scenario(e2e_engine):
    """
    SCÉNARIO COMPLET E2E DE CERTIFICATION (Section 21) :
    USER INTENT -> PLAN -> EXECUTION -> FAILURE -> RECOVERY -> REPLAN -> VERIFICATION -> FINAL RESULT.
    """
    contract = e2e_engine.create_mission_contract(
        objective="Research AI papers, write summary script, and generate final report",
        user_intent="Autonomous E2E Research and Code Pipeline",
        execution_budget=100.0,
        risk_level="R1",
    )

    plan_nodes = [
        {
            "node_id": "step_1_research",
            "type": "RESEARCH",
            "required_capability": "cap_web_search",
            "mock_output": {"sources_count": 5, "summary": "Found 5 relevant AI research papers"},
            "cost": 10.0,
        },
        {
            "node_id": "step_2_missing_cap_acquisition",
            "type": "TOOL",
            "required_capability": "PDF Processing",  # Capacité absente qui va être acquise via Self-Healing V10.8
            "mock_output": {"status": "SUCCESS"},
            "cost": 15.0,
        },
        {
            "node_id": "step_3_code_gen",
            "type": "CODE",
            "required_capability": "cap_code_editing",
            "mock_output": "print('Final report compiled successfully')",
            "cost": 10.0,
        },
    ]
    deps = {
        "step_2_missing_cap_acquisition": ["step_1_research"],
        "step_3_code_gen": ["step_2_missing_cap_acquisition"],
    }

    # 1. Build Plan
    plan_valid = e2e_engine.build_execution_plan(contract.mission_id, plan_nodes, deps)
    assert plan_valid is True

    # 2. Execute E2E Loop
    res = e2e_engine.execute_mission_e2e(contract.mission_id)

    # 3. Assert Final Result
    assert res["status"] == "COMPLETED"
    assert len(res["completed_nodes"]) == 3
    assert contract.current_state == MissionState.COMPLETED
    assert contract.completion_state == "SUCCESSFULLY_VERIFIED_END_TO_END"
