"""
Unit & E2E Integration Test Suite for E-ZZIO V10.11 — Continuous Autonomous Operations Control Loop.
"""
import shutil
import time
from pathlib import Path

import pytest

from core.agent.autonomous_e2e_engine import MissionState, autonomous_e2e_engine
from core.operations.continuous_operations_loop import (
    ContinuousOperationsControlLoop,
    ForecastRiskLevel,
    SystemOperatingMode,
)
from core.operations.multi_mission_arbitrator import (
    MissionPriority,
    MultiMissionArbitrator,
    ResourceStatus,
)


@pytest.fixture
def loop_instance():
    arb = MultiMissionArbitrator(max_concurrent_missions=2, total_worker_slots=2)
    return ContinuousOperationsControlLoop(arbitrator=arb)


def test_proactive_resource_forecasting_low_risk(loop_instance):
    forecast = loop_instance.forecast_operational_risks()

    assert forecast.risk_level == ForecastRiskLevel.LOW
    assert forecast.queue_pressure == 0.0
    assert forecast.worker_saturation == 0.0


def test_proactive_resource_forecasting_critical_risk(loop_instance):
    arb = loop_instance.arbitrator

    # Add 5 pending missions to saturate worker pool and create queue pressure
    for i in range(5):
        c = autonomous_e2e_engine.create_mission_contract(
            objective=f"Queue Saturation Mission {i}", user_intent="Saturate queue"
        )
        arb.register_mission(c, priority=MissionPriority.NORMAL)

    # Fill workers
    arb.workers["worker_1"].status = ResourceStatus.BUSY
    arb.workers["worker_2"].status = ResourceStatus.BUSY

    forecast = loop_instance.forecast_operational_risks()

    assert forecast.risk_level == ForecastRiskLevel.CRITICAL
    assert forecast.queue_pressure > 2.0
    assert forecast.worker_saturation == 1.0


def test_adaptive_throttling_mode_adjustment(loop_instance):
    forecast_critical = loop_instance.forecast_operational_risks()
    forecast_critical.risk_level = ForecastRiskLevel.CRITICAL

    mode = loop_instance.adjust_adaptive_throttling(forecast_critical)
    assert mode == SystemOperatingMode.EMERGENCY

    forecast_high = loop_instance.forecast_operational_risks()
    forecast_high.risk_level = ForecastRiskLevel.HIGH

    mode_high = loop_instance.adjust_adaptive_throttling(forecast_high)
    assert mode_high == SystemOperatingMode.THROTTLED


def test_continuous_control_cycle_execution(loop_instance):
    arb = loop_instance.arbitrator
    c = autonomous_e2e_engine.create_mission_contract(
        objective="Control Cycle Mission", user_intent="Test control cycle"
    )
    nodes = [{"node_id": "n1", "type": "FILE", "mock_output": {"exists": True}}]
    autonomous_e2e_engine.build_execution_plan(c.mission_id, nodes, {"n1": []})
    arb.register_mission(c, priority=MissionPriority.HIGH)

    cycle_res = loop_instance.run_control_cycle()

    assert cycle_res.cycle_id.startswith("cycle_1_")
    assert cycle_res.duration_seconds >= 0.0
    assert c.mission_id in cycle_res.executed_missions
    assert c.current_state == MissionState.COMPLETED


def test_degraded_worker_continuous_recovery(loop_instance):
    arb = loop_instance.arbitrator
    arb.workers["worker_1"].status = ResourceStatus.DEGRADED

    cycle_res = loop_instance.run_control_cycle()

    assert "worker_1" in cycle_res.recovered_workers
    assert arb.workers["worker_1"].status == ResourceStatus.AVAILABLE


def test_real_continuous_operations_e2e_scenario():
    """Real E2E scenario testing continuous operations loop over 10+ missions under dynamic load."""
    test_arb = MultiMissionArbitrator(max_concurrent_missions=3, total_worker_slots=3)
    loop = ContinuousOperationsControlLoop(arbitrator=test_arb)
    test_dir = Path("state/tmp/v10_11_disposable_loop_e2e")
    if test_dir.exists():
        shutil.rmtree(test_dir)
    test_dir.mkdir(parents=True, exist_ok=True)

    try:
        contracts = []
        for i in range(12):
            c = autonomous_e2e_engine.create_mission_contract(
                objective=f"Loop Mission {i}", user_intent="Continuous loop test"
            )
            out_f = test_dir / f"loop_out_{i}.txt"
            nodes = [{"node_id": f"n_{i}", "type": "FILE", "mock_output": {"exists": True, "path": str(out_f)}}]
            autonomous_e2e_engine.build_execution_plan(c.mission_id, nodes, {f"n_{i}": []})
            test_arb.register_mission(c, priority=MissionPriority.HIGH if i % 4 == 0 else MissionPriority.NORMAL)
            contracts.append(c)

        # Run control loop cycles until all missions complete
        completed_count = 0
        max_cycles = 15
        cycles_run = 0

        while completed_count < len(contracts) and cycles_run < max_cycles:
            res = loop.run_control_cycle()
            cycles_run += 1
            completed_count = len([c for c in contracts if c.current_state == MissionState.COMPLETED])

        assert completed_count == len(contracts)
        assert loop.cycle_count == cycles_run
        assert len(loop.history) == cycles_run

    finally:
        if test_dir.exists():
            shutil.rmtree(test_dir)
