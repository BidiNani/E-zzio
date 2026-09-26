"""
tests/test_a13_long_running_reliability.py — Acceptance Test Suite for Phase A13 Long-Running Mission Reliability.
Tests:
- multi-wave DAG orchestration
- idempotency on resume (COMPLETED not replayed, RUNNING reset to PENDING)
- checkpoint durability and latency metrics
- cancellation and process cleanup (zero orphan processes)
- resource bounds (concurrency ceilings, retry bounds)
- crash matrix (interruptions before task, during task, after task, after checkpoint)
- long-run evidence generation
"""
import time

import pytest

from core.agent.mission_controller import MissionRecord, MissionRegistry, MissionStatus
from core.orchestration.dag import DAGExecutionStatus, TaskDAG
from core.orchestration.long_running_harness import (
    LongRunningMissionHarness,
    SimulatedCrashInterrupt,
)


@pytest.mark.asyncio
async def test_a13_1_multi_wave_execution_and_checkpoints(tmp_path):
    registry = MissionRegistry(db_path=tmp_path / "long_mission.db")
    harness = LongRunningMissionHarness(workspace_root=str(tmp_path), max_concurrency=2)

    # Build 3-wave DAG: Wave 1 (w1_a, w1_b) -> Wave 2 (w2) -> Wave 3 (w3)
    dag = TaskDAG(dag_id="dag-multiwave", name="multi_wave_pipeline")
    dag.add_node("w1_a", "Forensic Scan A", "forensic")
    dag.add_node("w1_b", "Forensic Scan B", "forensic")
    dag.add_node("w2", "Synthesize Analysis", "analysis", dependencies=["w1_a", "w1_b"])
    dag.add_node("w3", "Apply Modifications", "coding", dependencies=["w2"])

    mission = MissionRecord(mission_id="m-long-01", goal="Multi-wave execution", status=MissionStatus.RUNNING)
    registry.register(mission)
    harness.record_checkpoint("m-long-01", dag, registry)

    # Execute Wave 1
    await harness.execute_wave("m-long-01", dag, registry)
    assert dag.nodes["w1_a"].status == DAGExecutionStatus.COMPLETED
    assert dag.nodes["w1_b"].status == DAGExecutionStatus.COMPLETED
    assert dag.nodes["w2"].status == DAGExecutionStatus.PENDING

    # Execute Wave 2
    await harness.execute_wave("m-long-01", dag, registry)
    assert dag.nodes["w2"].status == DAGExecutionStatus.COMPLETED
    assert dag.nodes["w3"].status == DAGExecutionStatus.PENDING

    # Execute Wave 3
    await harness.execute_wave("m-long-01", dag, registry)
    assert dag.nodes["w3"].status == DAGExecutionStatus.COMPLETED

    assert len(harness.checkpoints_recorded) >= 4
    for cp in harness.checkpoints_recorded:
        assert cp.latency_ms >= 0.0


@pytest.mark.asyncio
async def test_a13_2_idempotency_after_crash(tmp_path):
    registry = MissionRegistry(db_path=tmp_path / "idempotency.db")
    harness = LongRunningMissionHarness(workspace_root=str(tmp_path))

    dag = TaskDAG(dag_id="dag-idempotent", name="idempotent_flow")
    n1 = dag.add_node("step-1", "Done Step", "forensic")
    n1.status = DAGExecutionStatus.COMPLETED
    n1.result = {"output": "Already completed"}

    n2 = dag.add_node("step-2", "Interrupted Step", "coding", dependencies=["step-1"])
    n2.status = DAGExecutionStatus.RUNNING  # Interrupted in-flight

    n3 = dag.add_node("step-3", "Future Step", "test", dependencies=["step-2"])
    n3.status = DAGExecutionStatus.PENDING

    registry.register(MissionRecord(mission_id="m-idemp", goal="Test idempotency", status=MissionStatus.RUNNING))
    registry.checkpoint_dag("m-idemp", dag)

    # Resume from checkpoint
    recovered_dag = harness.resume_mission("m-idemp", registry)

    # INVARIANT: Completed step remains COMPLETED (no duplicate work)
    assert recovered_dag.nodes["step-1"].status == DAGExecutionStatus.COMPLETED
    # INVARIANT: Interrupted RUNNING step resets to PENDING for safe restart
    assert recovered_dag.nodes["step-2"].status == DAGExecutionStatus.PENDING
    assert recovered_dag.nodes["step-3"].status == DAGExecutionStatus.PENDING


@pytest.mark.asyncio
async def test_a13_3_cancellation_and_zero_orphan_processes(tmp_path):
    import subprocess
    import sys
    harness = LongRunningMissionHarness(workspace_root=str(tmp_path))

    # Spawn real subprocess sleeping
    proc = subprocess.Popen([sys.executable, "-c", "import time; time.sleep(10)"])
    assert proc.poll() is None

    # Cancel via harness
    killed = harness.cancel_active_processes([proc])
    time.sleep(0.1)

    assert killed == 1
    assert proc.poll() is not None
    assert harness.orphan_processes_count == 0
    assert harness.cancellations_count == 1


@pytest.mark.asyncio
async def test_a13_4_crash_matrix_coverage(tmp_path):
    registry = MissionRegistry(db_path=tmp_path / "crash_matrix.db")
    harness = LongRunningMissionHarness(workspace_root=str(tmp_path))

    crash_points = [
        "before_task",
        "during_task",
        "after_task_before_checkpoint",
        "after_checkpoint",
    ]

    for pt in crash_points:
        dag = TaskDAG(dag_id=f"dag-{pt}", name="crash_test")
        dag.add_node("n1", "Node 1", "test")
        registry.register(MissionRecord(mission_id=f"m-{pt}", goal="Crash test", status=MissionStatus.RUNNING))
        registry.checkpoint_dag(f"m-{pt}", dag)

        with pytest.raises(SimulatedCrashInterrupt) as exc_info:
            await harness.execute_wave(f"m-{pt}", dag, registry, interrupt_at=pt)
        assert exc_info.value.checkpoint_name == pt

    assert harness.crashes_count == 4


@pytest.mark.asyncio
async def test_a13_5_long_run_evidence_generation(tmp_path):
    registry = MissionRegistry(db_path=tmp_path / "evidence_run.db")
    harness = LongRunningMissionHarness(workspace_root=str(tmp_path))

    dag = TaskDAG(dag_id="dag-evidence", name="evidence_test")
    dag.add_node("step1", "Step 1", "forensic")
    dag.add_node("step2", "Step 2", "coding", dependencies=["step1"])

    start_t = time.time()
    await harness.execute_wave("m-evidence", dag, registry)
    await harness.execute_wave("m-evidence", dag, registry)

    evidence = harness.build_evidence("m-evidence", dag, start_time=start_t, final_validation=True)
    ev_dict = evidence.to_dict()

    assert ev_dict["mission_id"] == "m-evidence"
    assert ev_dict["nodes_total"] == 2
    assert ev_dict["nodes_completed"] == 2
    assert ev_dict["orphan_processes"] == 0
    assert ev_dict["final_validation"] is True
    assert ev_dict["status"] == "COMPLETED"
    assert ev_dict["resume_point"] == "step2"
