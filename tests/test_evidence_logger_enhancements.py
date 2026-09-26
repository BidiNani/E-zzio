"""Test evidence logger helper methods and get_evidence retrieval integration."""

import tempfile

from core.agent.evidence_logger import CodingTaskEvidence, EvidenceLogger


def test_coding_task_evidence_helpers():
    """Verify add_test_result, add_command_result and file deduplication on CodingTaskEvidence."""
    evidence = CodingTaskEvidence(task_id="task_test_123", plan="Test plan")

    # Deduplicated files
    evidence.files_changed.extend(["file_a.py", "file_b.py", "file_a.py"])
    evidence.add_command_result("pytest -q", exit_code=0, duration_ms=120)
    evidence.add_test_result("test_unit_a", passed=True, summary="1 passed")
    evidence.complete(result="SUCCESS", final_diff="--- diff ---")

    assert "file_a.py" in evidence.files_changed
    assert len(evidence.files_changed) == 2  # Deduplicated
    assert len(evidence.commands) == 1
    assert evidence.commands[0]["command"] == "pytest -q"
    assert len(evidence.tests) == 1
    assert evidence.tests[0]["name"] == "test_unit_a"
    assert evidence.tests[0]["passed"] is True


def test_evidence_logger_get_evidence():
    """Verify EvidenceLogger.get_evidence retrieves saved JSON evidence records."""
    with tempfile.TemporaryDirectory() as tmpdir:
        logger = EvidenceLogger(workspace_root=tmpdir)
        evidence = CodingTaskEvidence(task_id="task_rec_456", plan="Record plan")
        evidence.files_changed.append("core/service.py")
        evidence.add_test_result("test_service", passed=True, summary="OK")
        evidence.complete(result="SUCCESS")

        res_paths = logger.record_evidence(evidence)
        assert "json" in res_paths
        assert "markdown" in res_paths

        loaded = logger.get_evidence("task_rec_456")
        assert loaded is not None
        assert loaded["task_id"] == "task_rec_456"
        assert loaded["result"] == "SUCCESS"
        assert "core/service.py" in loaded["files_changed"]
        assert loaded["tests"][0]["name"] == "test_service"
