"""E2E Test for EzzioMaster Self-Coding Mission Convergence (Mission 22).

Verifies Channel/Master -> ExecutionDecisionEngine -> AutonomousSelfCodingLoop -> Pytest Empirical Validation -> Self-Correction -> CompletionGate -> Evidence.
"""

import os

import pytest

from core.ezzio_master import EzzioMaster


def test_ezzio_master_self_coding_e2e_flow(tmp_path):
    # Prepare mock codebase directory structure
    target_rel = "app/calculator.py"
    test_rel = "tests/test_calculator.py"

    target_full = tmp_path / "app" / "calculator.py"
    test_full = tmp_path / "tests" / "test_calculator.py"

    target_full.parent.mkdir(parents=True, exist_ok=True)
    test_full.parent.mkdir(parents=True, exist_ok=True)

    # Initial buggy code
    target_full.write_text("def add(a: int, b: int) -> int:\n    return a - b  # Bug!\n", encoding="utf-8")

    # Test asserting correct behavior
    test_full.write_text(
        "import sys\n"
        "from pathlib import Path\n"
        "sys.path.insert(0, str(Path(__file__).parent.parent / 'app'))\n"
        "from calculator import add\n\n"
        "def test_add():\n"
        "    assert add(2, 3) == 5\n",
        encoding="utf-8"
    )

    master = EzzioMaster(workspace_root=str(tmp_path))

    # Run self-coding mission with self-correction
    result = master.run_self_coding_mission(
        objective="Fix subtraction bug in calculator add function",
        target_file=target_rel,
        test_file=test_rel,
        search_block="return a - b  # Bug!",
        replace_block="return a + b  # Fixed",
        preferred_worker="native",
    )

    assert result.status == "COMPLETED"
    assert result.proof_status == "PROVEN"
    assert result.tests_passed == 1
    assert result.worker_used in ("native", "hermes", "cline", "pig")
    assert "return a + b" in target_full.read_text(encoding="utf-8")
