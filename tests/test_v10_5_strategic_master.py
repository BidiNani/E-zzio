"""
E-ZZIO V10.5 — Critical Test Suite: Strategic Master, Long-Horizon Planning, Goals & Scheduler Engine.
Couvre les tests unitaires et scénarios End-to-End exigés par la spécification V10.5.
"""

import subprocess
import sys
import time

import pytest

from core.agent.strategic_master import (
    GoalPriority,
    GoalStatus,
    RiskForecast,
    ScheduledTask,
    SchedulingMode,
    StrategicGoal,
    StrategicMasterEngine,
    strategic_master,
)


@pytest.fixture(autouse=True)
def setup_strategic_master():
    strategic_master.goals.clear()
    strategic_master.scheduled_tasks.clear()
    strategic_master.executed_dedup_keys.clear()
    strategic_master.risk_forecasts.clear()
    yield
    strategic_master.goals.clear()
    strategic_master.scheduled_tasks.clear()
    strategic_master.executed_dedup_keys.clear()
    strategic_master.risk_forecasts.clear()


def test_01_goal_creation_and_hierarchy():
    """1. Goal creation & hierarchy."""
    parent = strategic_master.create_goal(
        title="Programme V10 Optimization",
        description="Global platform performance program",
        priority=GoalPriority.CRITICAL,
    )
    assert parent.goal_id.startswith("goal_")
    assert parent.priority == GoalPriority.CRITICAL

    child = strategic_master.create_goal(
        title="Projet Speedup FAST PATH",
        description="Accelerate direct dialogue queries",
        priority=GoalPriority.HIGH,
        parent_goal_id=parent.goal_id,
    )
    assert child.parent_goal_id == parent.goal_id
    assert child.goal_id in parent.children_ids


def test_02_task_scheduling_and_idempotency():
    """2. Task scheduling & deduplication idempotency."""
    g = strategic_master.create_goal(title="Test Goal", description="Idempotency test")
    t1 = strategic_master.schedule_task(
        goal_id=g.goal_id,
        mode=SchedulingMode.RECURRING,
        cron_pattern="0 0 * * *",
        deduplication_key="dedup_daily_cleanup",
    )
    assert t1.mode == SchedulingMode.RECURRING

    # Duplicate call with same key -> returns existing task without creating duplicate
    t2 = strategic_master.schedule_task(
        goal_id=g.goal_id,
        mode=SchedulingMode.RECURRING,
        cron_pattern="0 0 * * *",
        deduplication_key="dedup_daily_cleanup",
    )
    assert t1.task_id == t2.task_id


def test_03_evaluate_progress_engine():
    """3. Evaluate progress engine."""
    parent = strategic_master.create_goal(title="Parent", description="Progress parent")
    child1 = strategic_master.create_goal(title="Child 1", description="Part 1", parent_goal_id=parent.goal_id)
    child2 = strategic_master.create_goal(title="Child 2", description="Part 2", parent_goal_id=parent.goal_id)

    child1.progress = 100.0
    child2.progress = 50.0

    prog = strategic_master.evaluate_progress(parent.goal_id)
    assert prog == 75.0
    assert parent.progress == 75.0


def test_04_05_06_risk_forecasting_and_dependencies():
    """4, 5, 6. Deadline & dependency risk forecasting."""
    dep_goal = strategic_master.create_goal(title="Blocked Dep", description="Failing dependency")
    dep_goal.status = GoalStatus.BLOCKED

    g = strategic_master.create_goal(
        title="Main Goal",
        description="Goal at risk",
        deadline=time.time() + 1800,  # 30 mins
        dependencies=[dep_goal.goal_id],
    )
    g.progress = 10.0

    forecasts = strategic_master.forecast_risks(g.goal_id)
    assert len(forecasts) >= 1
    risk_types = [f.risk_type for f in forecasts]
    assert "DEPENDENCY_BLOCKED" in risk_types


def test_07_what_if_simulation():
    """7. What-If simulation without state mutation."""
    g = strategic_master.create_goal(title="Sim Goal", description="Simulation test")
    sim = strategic_master.simulate_what_if(g.goal_id, "add worker CODER_WORKER")
    assert sim["simulation"] is True
    assert sim["estimated_risk"] == "LOW"
    assert g.status == GoalStatus.PLANNED  # State unmutated


def test_08_replanning_and_checkpoints():
    """8. Replanning & checkpoint recording."""
    g = strategic_master.create_goal(title="Replan Goal", description="Replanning test")
    ok = strategic_master.replan_goal(g.goal_id, reason="Provider outage recovered via fallback")
    assert ok is True
    assert len(g.checkpoints) == 1
    assert g.checkpoints[0]["event"] == "REPLANNED"


def test_09_kill_switch_goal_subtree():
    """9. Kill switch goal subtree cancellation."""
    parent = strategic_master.create_goal(title="Root Goal", description="Root")
    child = strategic_master.create_goal(title="Child Goal", description="Child", parent_goal_id=parent.goal_id)

    cancelled = strategic_master.cancel_goal_tree(parent.goal_id, reason="Emergency Shutdown")
    assert set(cancelled) == {parent.goal_id, child.goal_id}
    assert parent.status == GoalStatus.CANCELLED
    assert child.status == GoalStatus.CANCELLED


def test_10_frozen_core_check():
    """10. Frozen Core remains unchanged."""
    res = subprocess.run([sys.executable, "tools/check_frozen_core.py"], capture_output=True, text=True)
    assert res.returncode == 0
    assert "FROZEN_CORE_OK" in res.stdout
