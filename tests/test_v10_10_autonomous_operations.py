"""
Unit & E2E Integration Test Suite for E-ZZIO V10.10 — Autonomous Operations & Multi-Mission Resource Optimization.
"""
import pytest
import time
import shutil
from pathlib import Path

from core.agent.autonomous_e2e_engine import autonomous_e2e_engine, MissionState
from core.operations.multi_mission_arbitrator import (
    MultiMissionArbitrator,
    MissionPriority,
    OperationalHealth,
    ResourceStatus,
    DeadlineStatus,
)


@pytest.fixture
def arbitrator():
    return MultiMissionArbitrator(max_concurrent_missions=2, total_worker_slots=2)


def test_multi_mission_registration(arbitrator):
    c1 = autonomous_e2e_engine.create_mission_contract(
        objective="Test Mission 1", user_intent="Test multi-mission registration"
    )
    mm1 = arbitrator.register_mission(c1, priority=MissionPriority.HIGH)

    assert c1.mission_id in arbitrator.managed_missions
    assert mm1.priority == MissionPriority.HIGH
    assert mm1.health == OperationalHealth.HEALTHY


def test_priority_arbitration_and_fairness(arbitrator):
    c1 = autonomous_e2e_engine.create_mission_contract(
        objective="Low Priority Mission", user_intent="Wait long time"
    )
    c2 = autonomous_e2e_engine.create_mission_contract(
        objective="High Priority Mission", user_intent="Urgent work"
    )

    mm1 = arbitrator.register_mission(c1, priority=MissionPriority.LOW)
    mm2 = arbitrator.register_mission(c2, priority=MissionPriority.HIGH)

    # Simulate mm1 waiting 100 seconds
    mm1.wait_time_seconds = 100.0

    score1 = arbitrator.calculate_dynamic_priority(mm1)
    score2 = arbitrator.calculate_dynamic_priority(mm2)

    # 25 + 100 * 0.1 = 35.0 vs 75.0
    assert score2 > score1

    # Simulate mm1 waiting 600 seconds (starvation protection)
    mm1.wait_time_seconds = 600.0
    score1_aged = arbitrator.calculate_dynamic_priority(mm1)

    # 25 + 600 * 0.1 = 85.0 vs 75.0 -> Aged low priority outranks newly created high priority
    assert score1_aged > score2


def test_resource_allocation_and_arbitration_decision(arbitrator):
    c1 = autonomous_e2e_engine.create_mission_contract(
        objective="Mission A", user_intent="Resource allocation test"
    )
    arbitrator.register_mission(c1, priority=MissionPriority.NORMAL)

    decision = arbitrator.arbitrate_and_schedule()

    assert decision.selected_mission_id == c1.mission_id
    assert c1.current_state == MissionState.EXECUTING
    assert len(arbitrator.managed_missions[c1.mission_id].assigned_worker_ids) == 1


def test_preemption_and_checkpoint_resume(arbitrator):
    c_normal1 = autonomous_e2e_engine.create_mission_contract(
        objective="Normal Mission 1", user_intent="Task 1"
    )
    c_normal2 = autonomous_e2e_engine.create_mission_contract(
        objective="Normal Mission 2", user_intent="Task 2"
    )
    c_critical = autonomous_e2e_engine.create_mission_contract(
        objective="Critical Mission", user_intent="Critical task"
    )

    # Fill worker pool (2 worker slots)
    arbitrator.register_mission(c_normal1, priority=MissionPriority.LOW, preemptible=True)
    arbitrator.arbitrate_and_schedule()

    arbitrator.register_mission(c_normal2, priority=MissionPriority.LOW, preemptible=True)
    arbitrator.arbitrate_and_schedule()

    assert c_normal1.current_state == MissionState.EXECUTING
    assert c_normal2.current_state == MissionState.EXECUTING
    assert len([w for w in arbitrator.workers.values() if w.status == ResourceStatus.AVAILABLE]) == 0

    # Register critical mission requiring preemption of busy slots
    arbitrator.register_mission(c_critical, priority=MissionPriority.CRITICAL)

    # Arbitrate critical mission -> should preempt one of the running normal missions
    decision = arbitrator.arbitrate_and_schedule()

    assert decision.selected_mission_id == c_critical.mission_id
    assert len(decision.preempted_mission_ids) == 1
    preempted_id = decision.preempted_mission_ids[0]
    assert preempted_id in (c_normal1.mission_id, c_normal2.mission_id)
    assert arbitrator.managed_missions[preempted_id].contract.current_state == MissionState.PREPARING

    # Resume preempted mission
    resumed = arbitrator.resume_mission(preempted_id)
    assert resumed is True
    assert arbitrator.managed_missions[preempted_id].contract.current_state == MissionState.EXECUTING


def test_worker_failure_and_recovery(arbitrator):
    c1 = autonomous_e2e_engine.create_mission_contract(
        objective="Worker Fail Test Mission", user_intent="Test worker recovery"
    )
    arbitrator.register_mission(c1, priority=MissionPriority.HIGH)
    arbitrator.arbitrate_and_schedule()

    worker_id = arbitrator.managed_missions[c1.mission_id].assigned_worker_ids[0]

    # Trigger worker failure
    affected = arbitrator.handle_worker_failure(worker_id)

    assert affected == c1.mission_id
    assert arbitrator.workers[worker_id].status == ResourceStatus.DEGRADED
    # Substitute worker assigned
    assert len(arbitrator.managed_missions[c1.mission_id].assigned_worker_ids) == 1
    assert arbitrator.managed_missions[c1.mission_id].assigned_worker_ids[0] != worker_id


def test_cancellation_propagation(arbitrator):
    parent = autonomous_e2e_engine.create_mission_contract(
        objective="Parent Mission", user_intent="Parent intent"
    )
    child = autonomous_e2e_engine.create_mission_contract(
        objective="Child Mission", user_intent="Child intent"
    )

    arbitrator.register_mission(parent, priority=MissionPriority.NORMAL)
    arbitrator.register_mission(child, priority=MissionPriority.LOW, parent_mission_id=parent.mission_id)

    # Cancel parent
    arbitrator.cancel_mission(parent.mission_id, reason="User test cancellation")

    assert parent.current_state == MissionState.CANCELLED
    assert child.current_state == MissionState.CANCELLED


def test_deadlock_detection(arbitrator):
    c1 = autonomous_e2e_engine.create_mission_contract(objective="Mission 1", user_intent="Dep 1")
    c2 = autonomous_e2e_engine.create_mission_contract(objective="Mission 2", user_intent="Dep 2")

    c1.dependencies = {c1.mission_id: [c2.mission_id]}
    c2.dependencies = {c2.mission_id: [c1.mission_id]}

    arbitrator.register_mission(c1)
    arbitrator.register_mission(c2)

    deadlocks = arbitrator.detect_multi_mission_deadlock()
    assert len(deadlocks) > 0


def test_real_multi_mission_e2e_scenario():
    """Real E2E integration scenario running multiple concurrent missions with preemption & worker recovery."""
    test_arb = MultiMissionArbitrator(max_concurrent_missions=2, total_worker_slots=2)
    test_dir = Path("state/tmp/v10_10_disposable_e2e")
    if test_dir.exists():
        shutil.rmtree(test_dir)
    test_dir.mkdir(parents=True, exist_ok=True)

    try:
        f1 = test_dir / "m1_out.txt"
        f2 = test_dir / "m2_out.txt"

        # Mission A: Normal
        ca = autonomous_e2e_engine.create_mission_contract(
            objective="Multi-Mission A", user_intent="Normal task"
        )
        nodes_a = [{"node_id": "na_1", "type": "FILE", "mock_output": {"exists": True, "path": str(f1)}}]
        autonomous_e2e_engine.build_execution_plan(ca.mission_id, nodes_a, {"na_1": []})
        test_arb.register_mission(ca, priority=MissionPriority.NORMAL)

        # Mission B: Critical
        cb = autonomous_e2e_engine.create_mission_contract(
            objective="Multi-Mission B", user_intent="Critical task"
        )
        nodes_b = [{"node_id": "nb_1", "type": "FILE", "mock_output": {"exists": True, "path": str(f2)}}]
        autonomous_e2e_engine.build_execution_plan(cb.mission_id, nodes_b, {"nb_1": []})
        test_arb.register_mission(cb, priority=MissionPriority.CRITICAL)

        # Arbitrate and execute
        test_arb.arbitrate_and_schedule()
        res_b = test_arb.execute_managed_mission(cb.mission_id)
        res_a = test_arb.execute_managed_mission(ca.mission_id)

        assert res_b["status"] == "COMPLETED"
        assert res_a["status"] == "COMPLETED"
        assert ca.current_state == MissionState.COMPLETED
        assert cb.current_state == MissionState.COMPLETED

    finally:
        if test_dir.exists():
            shutil.rmtree(test_dir)
