"""
E-ZZIO Core V9.2 — Autonomous Validation & Self-Correction E2E Test Suite.
Verifies the end-to-end self-correction pipeline:
EXECUTE -> VALIDATE -> DETECT FAILURE -> DIAGNOSE -> REPAIR -> RETEST -> VALIDATE -> COMPLETE
"""
import sys
from collections.abc import AsyncIterator

import pytest

from core.ezzio_master import EzzioMaster
from core.orchestration.dag import DAGExecutionStatus, TaskDAG
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

    # Proof relative file resolution with custom workspace_root
    engine_ws = AutonomousSelfCorrectionEngine(workspace_root=str(tmp_path))
    proof_rel_ok = engine_ws.validate_proof("some output", expected_assertions={"required_files": ["existing.txt"]})
    assert proof_rel_ok.is_valid is True


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


@pytest.mark.asyncio
async def test_e2e_calculator_self_correction_and_crash_recovery(tmp_path):
    """Scenario:
    inspect -> defect -> modify -> test FAIL -> diagnose -> repair -> test PASS -> validate -> checkpoint -> recovery.
    """
    proj_dir = tmp_path / "calc_proj"
    proj_dir.mkdir(parents=True, exist_ok=True)
    calc_file = proj_dir / "calculator.py"
    test_file = proj_dir / "test_calculator.py"

    # Defective implementation (subtraction instead of addition)
    calc_file.write_text("def add(a: int, b: int) -> int:\n    return a - b\n", encoding="utf-8")
    test_file.write_text(
        "import sys\n"
        "from pathlib import Path\n"
        "sys.path.insert(0, str(Path(__file__).parent))\n"
        "from calculator import add\n\n"
        "def test_add():\n"
        "    assert add(2, 3) == 5\n",
        encoding="utf-8",
    )

    db_path = tmp_path / "missions_calc.db"
    audit_db_path = tmp_path / "audit_calc.db"
    from core.agent.mission_controller import MissionRecord, MissionRegistry, MissionStatus
    registry = MissionRegistry(db_path=db_path)
    ledger = AuditLedger(db_path=str(audit_db_path), workspace_root=str(tmp_path))
    orchestrator = DAGOrchestrator(audit_ledger=ledger)

    dag = TaskDAG(dag_id="dag-calc-repair", name="calculator_repair_flow")
    node = dag.add_node(
        task_id="task-fix-calc",
        title="Fix Calculator Bug",
        action_type="coding",
        max_retries=2,
    )

    mission_rec = MissionRecord(
        mission_id="calc-repair-m1",
        goal="Fix calculator addition bug",
        status=MissionStatus.RUNNING,
    )
    registry.register(mission_rec)

    # 1. First execution fails test
    engine = AutonomousSelfCorrectionEngine(audit_ledger=ledger)

    # Simuler le premier test échoué
    import subprocess
    first_test_res = subprocess.run(
        [sys.executable, "-m", "pytest", str(test_file)],
        capture_output=True,
        text=True,
    )
    assert first_test_res.returncode != 0

    # 2. Diagnostic & Repair
    diag = engine.diagnose_failure(
        task_id="task-fix-calc",
        output_or_error=first_test_res.stdout + first_test_res.stderr,
    )
    assert diag.failure_type == FailureType.ASSERTION_FAILED
    assert diag.repairable is True

    repair_plan = engine.generate_repair_plan(
        task_id="task-fix-calc",
        diagnosis=diag,
        attempt=1,
        max_attempts=2,
        original_prompt="Fix add function in calculator.py",
    )
    assert repair_plan.repair_action == "FIX_ASSERTION_FAILURE"

    # 3. Apply Repair (Modify file)
    calc_file.write_text("def add(a: int, b: int) -> int:\n    return a + b\n", encoding="utf-8")

    # 4. Retest & Empirical Validation
    second_test_res = subprocess.run(
        [sys.executable, "-m", "pytest", str(test_file)],
        capture_output=True,
        text=True,
    )
    assert second_test_res.returncode == 0

    proof = engine.validate_proof(
        second_test_res.stdout,
        expected_assertions={"required_files": [str(calc_file)], "contains": ["passed"]},
    )
    assert proof.is_valid is True

    # Mark node COMPLETED & Checkpoint
    node.status = DAGExecutionStatus.COMPLETED
    node.result = {
        "output": second_test_res.stdout,
        "self_correction_applied": True,
        "repair_history": [{"attempt": 1, "diagnosis": diag.to_dict()}],
        "validation_proof": proof.to_dict(),
    }
    registry.checkpoint_dag("calc-repair-m1", dag)

    # 5. Crash Simulation & Recovery Verification
    registry_v2 = MissionRegistry(db_path=db_path)
    loaded_checkpoint = registry_v2.get_dag_checkpoint("calc-repair-m1")
    loaded_dag = TaskDAG.from_dict(loaded_checkpoint)
    loaded_node = loaded_dag.nodes["task-fix-calc"]

    assert loaded_node.status == DAGExecutionStatus.COMPLETED
    assert loaded_node.result["validation_proof"]["is_valid"] is True
    assert loaded_node.result["self_correction_applied"] is True

