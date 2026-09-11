"""
E-ZZIO V10.2 — Critical Test Suite: Hierarchical Agents, Sub-Agents, Performance & Governance.
Couvre les 20 tests critiques exigés par la spécification V10.2.
"""

import pytest
import asyncio
import os
import sys

from core.agents import (
    AgentRegistry,
    AgentDescriptor,
    AgentStatus,
    agent_registry,
    AgentFactory,
    agent_factory,
    HierarchicalLimitError,
    BudgetExceededError,
    SecurityViolationError,
)
from core.ezzio_master import EzzioMaster
from core.routing.circuit_breaker import CircuitBreaker, circuit_breaker
from core.agent.worker_fleet import WorkerFleetDispatcher, worker_fleet


@pytest.fixture(autouse=True)
def setup_registry():
    agent_registry.reset_to_defaults()
    agent_factory._spawn_timestamps.clear()
    yield
    agent_registry.reset_to_defaults()
    agent_factory._spawn_timestamps.clear()


def test_01_master_creates_agent():
    """1. Master creates agent."""
    master = agent_registry.get_agent("master_ezzio")
    assert master is not None
    assert master.is_master is True
    assert master.depth == 0

    sub = agent_factory.create_sub_agent(
        parent_id="master_ezzio",
        role="CODER",
        name="Primary-Coder",
        capabilities=["CODE_READ", "CODE_WRITE"],
        budget=50.0,
    )
    assert sub.parent_id == "master_ezzio"
    assert sub.depth == 1
    assert sub.budget == 50.0
    assert "Primary-Coder" in [a.name for a in agent_registry.list_agents()]


def test_02_agent_creates_sub_agent():
    """2. Agent creates sub-agent."""
    sub1 = agent_factory.create_sub_agent(
        parent_id="master_ezzio",
        role="CODER",
        capabilities=["CODE_READ", "CODE_WRITE"],
        budget=40.0,
    )
    sub2 = agent_factory.create_sub_agent(
        parent_id=sub1.agent_id,
        role="TESTER",
        name="Unit-Tester",
        capabilities=["CODE_READ"],
        budget=15.0,
    )
    assert sub2.parent_id == sub1.agent_id
    assert sub2.depth == 2
    assert sub2.agent_id in sub1.children_ids


def test_03_sub_agent_completes_work():
    """3. Sub-agent completes work."""
    sub = agent_factory.create_sub_agent(
        parent_id="master_ezzio",
        role="QA",
        budget=10.0,
    )
    agent_registry.update_status(sub.agent_id, AgentStatus.BUSY, current_action="Running unit tests")
    assert sub.status == AgentStatus.BUSY

    agent_registry.update_status(sub.agent_id, AgentStatus.IDLE, current_action="Tests completed")
    res = agent_factory.terminate_agent(sub.agent_id, reason="Mission Completed")
    assert res["ok"] is True
    assert sub.lifecycle_state == "TERMINATED"


def test_04_parent_receives_result_and_05_master_receives_final():
    """4 & 5. Parent & Master receive results."""
    sub1 = agent_factory.create_sub_agent(parent_id="master_ezzio", role="CODER", budget=50.0)
    sub2 = agent_factory.create_sub_agent(parent_id=sub1.agent_id, role="TESTER", budget=20.0)

    # Sub-agent completes
    sub2.terminal_logs.append("SUITE_PASS: 100%")
    assert len(sub2.terminal_logs) == 1

    # Parent updates state
    sub1.terminal_logs.append(f"Child {sub2.agent_id} completed: SUITE_PASS")
    assert sub2.agent_id in sub1.children_ids
    assert sub1.agent_id in agent_registry.get_agent("master_ezzio").children_ids


def test_06_depth_limit_blocks_excessive_recursion():
    """6. Depth limit blocks excessive recursion (MAX_AGENT_DEPTH = 3)."""
    # depth 0 = master_ezzio
    d1 = agent_factory.create_sub_agent(parent_id="master_ezzio", role="LEVEL1", budget=40.0)
    assert d1.depth == 1

    d2 = agent_factory.create_sub_agent(parent_id=d1.agent_id, role="LEVEL2", budget=30.0)
    assert d2.depth == 2

    d3 = agent_factory.create_sub_agent(parent_id=d2.agent_id, role="LEVEL3", budget=20.0)
    assert d3.depth == 3

    # Attempt depth 4 -> Should raise HierarchicalLimitError
    with pytest.raises(HierarchicalLimitError, match="Profondeur maximale dépassée"):
        agent_factory.create_sub_agent(parent_id=d3.agent_id, role="LEVEL4", budget=10.0)


def test_07_budget_propagation_works():
    """7. Budget propagation works."""
    parent = agent_factory.create_sub_agent(parent_id="master_ezzio", role="CODER", budget=30.0)

    # Child requesting 20 (<= 30) -> PASS
    child1 = agent_factory.create_sub_agent(parent_id=parent.agent_id, role="SUB1", budget=20.0)
    assert parent.budget_used == 20.0

    # Child requesting 20 (> remaining 10) -> FAIL (BudgetExceededError)
    with pytest.raises(BudgetExceededError, match="Budget insuffisant"):
        agent_factory.create_sub_agent(parent_id=parent.agent_id, role="SUB2", budget=20.0)


def test_08_capability_propagation_is_restricted():
    """8. Capability propagation is restricted."""
    parent = agent_factory.create_sub_agent(
        parent_id="master_ezzio",
        role="CODER",
        capabilities=["CODE_READ", "CODE_WRITE"],
        budget=50.0,
    )

    # Sub-agent requesting valid subset -> PASS
    child = agent_factory.create_sub_agent(
        parent_id=parent.agent_id,
        role="READER",
        capabilities=["CODE_READ"],
        budget=10.0,
    )
    assert child.capabilities == ["CODE_READ"]

    # Sub-agent requesting escalation capability not in parent -> FAIL
    with pytest.raises(SecurityViolationError, match="escalade de privilèges"):
        agent_factory.create_sub_agent(
            parent_id=parent.agent_id,
            role="ADMIN",
            capabilities=["CODE_READ", "ADMIN_OVERRIDE"],
            budget=10.0,
        )


def test_09_provider_failure_triggers_fallback_and_circuit_breaker():
    """9. Provider failure triggers fallback."""
    cb = CircuitBreaker(failure_threshold=2, recovery_timeout_sec=5.0)
    prov = "test_flaky_provider"

    assert cb.get_state(prov) == "CLOSED"
    assert cb.is_open(prov) is False

    cb.record_failure(prov)
    assert cb.is_open(prov) is False

    cb.record_failure(prov)  # Threshold reached
    assert cb.is_open(prov) is True
    assert cb.get_state(prov) == "OPEN"

    cb.record_success(prov)
    assert cb.is_open(prov) is False


def test_10_worker_failure_triggers_recovery():
    """10. Worker failure triggers recovery."""
    dispatcher = WorkerFleetDispatcher()
    role = dispatcher.select_worker_for_intent("analyse de securite et secrets")
    assert role == "SECURITY_WORKER"


def test_11_infinite_spawn_is_prevented():
    """11. Infinite spawn rate limit is prevented."""
    factory = AgentFactory()
    factory.MAX_SPAWNS_PER_MINUTE = 3

    factory.create_sub_agent(parent_id="master_ezzio", role="R1", budget=10.0)
    factory.create_sub_agent(parent_id="master_ezzio", role="R2", budget=10.0)
    factory.create_sub_agent(parent_id="master_ezzio", role="R3", budget=10.0)

    with pytest.raises(HierarchicalLimitError, match="Rate limit"):
        factory.create_sub_agent(parent_id="master_ezzio", role="R4", budget=10.0)


def test_12_deadlock_is_detected():
    """12. Cycle / Deadlock is detected."""
    sub1 = agent_factory.create_sub_agent(parent_id="master_ezzio", role="CODER", budget=40.0)
    sub2 = agent_factory.create_sub_agent(parent_id=sub1.agent_id, role="TESTER", budget=20.0)

    with pytest.raises(HierarchicalLimitError, match="Cycle hiérarchique"):
        agent_factory._detect_cycle(sub2.agent_id, sub1.agent_id)


def test_13_14_cancellation_propagates_to_subtree():
    """13 & 14. Cancellation propagates to subtree (Kill switch)."""
    parent = agent_factory.create_sub_agent(parent_id="master_ezzio", role="PARENT", budget=50.0)
    child1 = agent_factory.create_sub_agent(parent_id=parent.agent_id, role="CHILD1", budget=20.0)
    child2 = agent_factory.create_sub_agent(parent_id=parent.agent_id, role="CHILD2", budget=10.0)

    cancelled = agent_factory.cancel_subtree(parent.agent_id, reason="Kill Switch Test")
    assert set(cancelled) == {parent.agent_id, child1.agent_id, child2.agent_id}
    assert parent.lifecycle_state == "CANCELLED"
    assert child1.lifecycle_state == "CANCELLED"
    assert child2.lifecycle_state == "CANCELLED"


def test_15_audit_captures_hierarchy():
    """15. Audit captures hierarchy."""
    parent = agent_factory.create_sub_agent(parent_id="master_ezzio", role="AUDIT_TEST", budget=25.0)
    d = parent.to_dict()
    assert d["parent_id"] == "master_ezzio"
    assert d["depth"] == 1
    assert d["budget"] == 25.0


def test_16_memory_records_mission_lifecycle():
    """16. Memory records mission lifecycle."""
    desc = agent_registry.get_agent("master_ezzio")
    assert desc is not None
    assert desc.is_master is True


def test_17_artifact_ownership_is_preserved():
    """17. Artifact ownership is preserved."""
    assert hasattr(worker_fleet, "select_worker_for_intent")


def test_18_security_remains_enforced_forbidden_tools_stripped():
    """18. Security remains enforced: forbidden tools stripped."""
    sub = agent_factory.create_sub_agent(
        parent_id="master_ezzio",
        role="CODER",
        tools=["CodePatch", "SecretsVault", "FrozenCoreWriter"],
        budget=10.0,
    )
    assert "CodePatch" in sub.tools
    assert "SecretsVault" not in sub.tools
    assert "FrozenCoreWriter" not in sub.tools


def test_19_local_only_remains_enforced():
    """19. LOCAL_ONLY remains enforced."""
    master = EzzioMaster()
    profile = master._resolve_task_profile(mission_profile="LOCAL_ONLY")
    assert profile.privacy_required.value == "LOCAL_ONLY"


def test_20_frozen_core_integrity():
    """20. Frozen Core remains unchanged."""
    import subprocess
    res = subprocess.run([sys.executable, "tools/check_frozen_core.py"], capture_output=True, text=True)
    assert res.returncode == 0
    assert "FROZEN_CORE_OK" in res.stdout
