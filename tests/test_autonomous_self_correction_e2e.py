"""
E-ZZIO Core V9.2 — Autonomous Validation & Self-Correction E2E Test Suite.
Verifies the end-to-end self-correction pipeline:
EXECUTE -> VALIDATE -> DETECT FAILURE -> DIAGNOSE -> REPAIR -> RETEST -> VALIDATE -> COMPLETE
"""
from collections.abc import AsyncIterator

import pytest

from core.ezzio_master import EzzioMaster
from core.orchestration.dag import TaskDAG
from core.orchestration.engine import DAGOrchestrator
from core.orchestration.self_correction import (
    AutonomousSelfCorrectionEngine,
    BoundedRepairPlan,
    FailureType,
    ValidationProof,
)
from core.providers.base_provider import (
    BaseProvider,
    CostClass,
    ProviderAvailability,
    ProviderErrorClass,
    ProviderResponse,
)
from core.security.audit_ledger import AuditLedger


class MockFailingProvider(BaseProvider):
    """Mock provider simulating initial failure followed by success on retry."""

    def __init__(self):
        super().__init__()
        self.name = "mock_failing"
        self.call_count = 0

    def availability(self) -> ProviderAvailability:
        return ProviderAvailability.AVAILABLE

    def cost_class(self, model: str | None = None) -> CostClass:
        return CostClass.LOCAL

    def capabilities(self, model: str | None = None) -> list[str]:
        return ["chat", "text"]

    def error_mapping(self, exc: Exception) -> ProviderErrorClass:
        return ProviderErrorClass.UNKNOWN_ERROR

    def health(self) -> dict:
        return {"status": "ok"}

    async def stream(self, prompt: str, **kwargs) -> AsyncIterator[str]:
        yield f"stream:{prompt}"

    async def generate(self, prompt: str, **kwargs) -> ProviderResponse:
        self.call_count += 1
        if self.call_count == 1:
            # First attempt produces empty response
            return ProviderResponse(content="", model="mock", provider="mock_failing")
        # Second attempt succeeds
        return ProviderResponse(
            content=f"[REPAIRED_OUTPUT] Successfully self-corrected on attempt {self.call_count}.",
            model="mock",
            provider="mock_failing",
        )


class MockAlwaysFailingProvider(BaseProvider):
    """Mock provider simulating persistent failure exceeding retry bounds."""

    def __init__(self):
        super().__init__()
        self.name = "mock_always_failing"
        self.call_count = 0

    def availability(self) -> ProviderAvailability:
        return ProviderAvailability.AVAILABLE

    def cost_class(self, model: str | None = None) -> CostClass:
        return CostClass.LOCAL

    def capabilities(self, model: str | None = None) -> list[str]:
        return ["chat", "text"]

    def error_mapping(self, exc: Exception) -> ProviderErrorClass:
        return ProviderErrorClass.UNKNOWN_ERROR

    def health(self) -> dict:
        return {"status": "ok"}

    async def stream(self, prompt: str, **kwargs) -> AsyncIterator[str]:
        yield f"stream:{prompt}"

    async def generate(self, prompt: str, **kwargs) -> ProviderResponse:
        self.call_count += 1
        return ProviderResponse(content="", model="mock", provider="mock_always_failing")


@pytest.mark.asyncio
async def test_failure_diagnosis_classification():
    engine = AutonomousSelfCorrectionEngine()

    diag_empty = engine.diagnose_failure("t1", "")
    assert diag_empty.failure_type == FailureType.EMPTY_OUTPUT
    assert diag_empty.repairable is True

    diag_syntax = engine.diagnose_failure("t2", "SyntaxError: invalid syntax at line 4")
    assert diag_syntax.failure_type == FailureType.SYNTAX_ERROR
    assert diag_syntax.repairable is True

    diag_missing = engine.diagnose_failure("t3", "FileNotFoundError: Target file missing: test.py")
    assert diag_missing.failure_type == FailureType.MISSING_ARTIFACT
    assert diag_missing.repairable is True

    diag_assert = engine.diagnose_failure("t4", "AssertionError: Expected 5, got 0")
    assert diag_assert.failure_type == FailureType.ASSERTION_FAILED
    assert diag_assert.repairable is True

    diag_policy = engine.diagnose_failure("t5", "[POLICY_DENIED] Restricted path access")
    assert diag_policy.failure_type == FailureType.POLICY_BLOCKED
    assert diag_policy.repairable is False


@pytest.mark.asyncio
async def test_repair_plan_generation():
    engine = AutonomousSelfCorrectionEngine()
    diag = engine.diagnose_failure("task-01", "SyntaxError: invalid syntax")

    plan = engine.generate_repair_plan(
        task_id="task-01",
        diagnosis=diag,
        attempt=1,
        max_attempts=2,
        original_prompt="Write helper function",
    )

    assert isinstance(plan, BoundedRepairPlan)
    assert plan.attempt == 1
    assert plan.max_attempts == 2
    assert plan.repair_action == "CORRECT_SYNTAX"
    assert "[AUTO-REPAIR ATTEMPT 1/2]" in plan.remediation_prompt
    assert "CORRECT_SYNTAX" in str(plan.to_dict()["repair_action"])


@pytest.mark.asyncio
async def test_validation_proof_verification(tmp_path):
    engine = AutonomousSelfCorrectionEngine()

    # Proof valid output
    proof_ok = engine.validate_proof("Valid response content")
    assert isinstance(proof_ok, ValidationProof)
    assert proof_ok.is_valid is True
    assert proof_ok.evidence_type == "EMPIRICAL_PROOF"

    # Proof empty output
    proof_empty = engine.validate_proof("")
    assert proof_empty.is_valid is False
    assert proof_empty.evidence_type == "EMPTY_OUTPUT"

    # Proof missing required file
    req_file = str(tmp_path / "nonexistent.txt")
    proof_missing = engine.validate_proof("some output", expected_assertions={"required_files": [req_file]})
    assert proof_missing.is_valid is False
    assert proof_missing.evidence_type == "MISSING_FILE"

    # Proof file exists
    existing_file = str(tmp_path / "existing.txt")
    with open(existing_file, "w") as f:
        f.write("data")
    proof_file_ok = engine.validate_proof("some output", expected_assertions={"required_files": [existing_file]})
    assert proof_file_ok.is_valid is True


@pytest.mark.asyncio
async def test_autonomous_self_correction_loop_success(tmp_path):
    mock_prov = MockFailingProvider()
    master = EzzioMaster(provider=mock_prov, workspace_root=str(tmp_path))

    subtasks = [
        {
            "task_id": "subtask-repair-01",
            "role": "coding",
            "prompt": "Generates module code",
            "complexity": 0.5,
            "dependencies": [],
        }
    ]

    res = await master.orchestrate_multi_agent_mission(
        mission_prompt="Autonomous repair mission test",
        subtask_specs=subtasks,
        max_retries=2,
    )

    assert res["ok"] is True
    assert len(res["subtasks"]) == 1
    sub_res = res["subtasks"][0]
    assert sub_res["status"] == "SUCCESS"
    assert sub_res["validated"] is True
    assert sub_res.get("self_correction_applied") is True
    assert len(sub_res.get("repair_history", [])) == 1
    assert sub_res["repair_history"][0]["attempt"] == 1


@pytest.mark.asyncio
async def test_autonomous_self_correction_exhausted_fail_closed(tmp_path):
    mock_prov = MockAlwaysFailingProvider()
    master = EzzioMaster(provider=mock_prov, workspace_root=str(tmp_path))

    subtasks = [
        {
            "task_id": "subtask-always-fail-01",
            "role": "coding",
            "prompt": "Will fail persistently",
            "complexity": 0.5,
            "dependencies": [],
        }
    ]

    res = await master.orchestrate_multi_agent_mission(
        mission_prompt="Persistent failure test",
        subtask_specs=subtasks,
        max_retries=1,
    )

    assert res["ok"] is False
    sub_res = res["subtasks"][0]
    assert sub_res["status"] in ("FAILED", "SKIPPED")
    assert "Self-correction exhausted" in str(sub_res.get("output")) or "Validation failed" in str(sub_res.get("output"))


@pytest.mark.asyncio
async def test_checkpoint_recovery_with_self_correction_state(tmp_path):
    ledger = AuditLedger(db_path=str(tmp_path / "audit.db"))
    orchestrator = DAGOrchestrator(audit_ledger=ledger)

    dag = TaskDAG(dag_id="dag-sc-checkpoint", name="self_correction_checkpoint_test")
    node = dag.add_node(
        task_id="node-1",
        title="Coding Task",
        action_type="coding",
        max_retries=2,
    )
    node.retry_count = 1
    node.result = {
        "status": "RUNNING",
        "repair_history": [{"attempt": 1, "diagnosis": {"failure_type": "EMPTY_OUTPUT"}}],
    }

    from core.agent.mission_controller import MissionRecord, MissionStatus, mission_registry
    mission_rec = MissionRecord(
        mission_id="sc-checkpoint-m1",
        goal="Test checkpoint",
        status=MissionStatus.RUNNING,
    )
    mission_registry.register(mission_rec)
    mission_registry.checkpoint_dag("sc-checkpoint-m1", dag)

    # Reload checkpoint
    loaded_dag_dict = mission_registry.get_dag_checkpoint("sc-checkpoint-m1")
    assert loaded_dag_dict is not None
    loaded_dag = TaskDAG.from_dict(loaded_dag_dict)
    loaded_node = loaded_dag.nodes["node-1"]

    assert loaded_node.retry_count == 1
    assert loaded_node.result["repair_history"][0]["attempt"] == 1
