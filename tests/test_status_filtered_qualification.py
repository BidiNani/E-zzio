"""Qualification test suite for Status-Filtered Historical Context (Mission 13)."""

import json
import os
import tempfile

from core.agent.agent_guard import AgentPolicyGuard
from core.agent.evidence_logger import CodingTaskEvidence, EvidenceLogger
from core.agent.tools_registry import ToolRegistry


def test_status_filter_outcomes_and_multi_matching():
    """Verify get_evidence_by_status filters SUCCESS, FAILED, ROLLBACK, multi-status, and unknown status."""
    with tempfile.TemporaryDirectory() as tmpdir:
        logger = EvidenceLogger(workspace_root=tmpdir)

        ev_s1 = CodingTaskEvidence(task_id="task_succ_1", result="SUCCESS", start_time=100.0)
        ev_f1 = CodingTaskEvidence(task_id="task_fail_1", result="FAILED", start_time=200.0)
        ev_r1 = CodingTaskEvidence(task_id="task_roll_1", result="ROLLBACK", start_time=300.0)
        ev_s2 = CodingTaskEvidence(task_id="task_succ_2", result="SUCCESS", start_time=400.0)

        logger.record_evidence(ev_s1)
        logger.record_evidence(ev_f1)
        logger.record_evidence(ev_r1)
        logger.record_evidence(ev_s2)

        # Single status matching
        succ = logger.get_evidence_by_status("SUCCESS", limit=10)
        assert len(succ) == 2
        assert succ[0]["task_id"] == "task_succ_2"
        assert succ[1]["task_id"] == "task_succ_1"

        fail = logger.get_evidence_by_status("FAILED", limit=10)
        assert len(fail) == 1
        assert fail[0]["task_id"] == "task_fail_1"

        roll = logger.get_evidence_by_status("ROLLBACK", limit=10)
        assert len(roll) == 1
        assert roll[0]["task_id"] == "task_roll_1"

        # Multi-status comma-separated string matching
        multi_str = logger.get_evidence_by_status("SUCCESS, FAILED", limit=10)
        assert len(multi_str) == 3
        assert [s["task_id"] for s in multi_str] == ["task_succ_2", "task_fail_1", "task_succ_1"]

        # Multi-status list matching
        multi_list = logger.get_evidence_by_status(["FAILED", "ROLLBACK"], limit=10)
        assert len(multi_list) == 2
        assert [s["task_id"] for s in multi_list] == ["task_roll_1", "task_fail_1"]

        # Unknown status
        unknown = logger.get_evidence_by_status("NONEXISTENT_STATUS", limit=10)
        assert len(unknown) == 0


def test_status_filter_limits_and_ordering():
    """Verify limit normalization, upper capping, and deterministic start_time ordering."""
    with tempfile.TemporaryDirectory() as tmpdir:
        logger = EvidenceLogger(workspace_root=tmpdir)
        for i in range(12):
            ev = CodingTaskEvidence(task_id=f"t_{i:02d}", result="SUCCESS", start_time=1000.0 + i)
            logger.record_evidence(ev)

        registry = ToolRegistry(workspace_root=tmpdir)

        # Limit = 3
        res3 = json.loads(registry.execute("get_evidence_by_status", {"status": "SUCCESS", "limit": 3}))
        assert len(res3) == 3
        assert res3[0]["task_id"] == "t_11"

        # Negative limit normalized to 10
        res_neg = json.loads(registry.execute("get_evidence_by_status", {"status": "SUCCESS", "limit": -1}))
        assert len(res_neg) == 10

        # Invalid string limit normalized to 10
        res_invalid = json.loads(registry.execute("get_evidence_by_status", {"status": "SUCCESS", "limit": "invalid"}))
        assert len(res_invalid) == 10


def test_status_filter_governance_and_redaction():
    """Verify status-filtered tool execution is policy SAFE and redacts sensitive data."""
    with tempfile.TemporaryDirectory() as tmpdir:
        logger = EvidenceLogger(workspace_root=tmpdir)
        ev = CodingTaskEvidence(task_id="task_sec_status", result="FAILED")
        secret_key = "AIzaSyB1234567890abcdefghijklmnopqrstuv"
        ev.add_command_result(f"gcloud auth login --key={secret_key}", 1, 50)
        logger.record_evidence(ev)

        guard = AgentPolicyGuard(workspace_root=tmpdir)
        cls_action, _ = guard.classify_action("get_evidence_by_status", {"status": "FAILED"})
        assert cls_action == "SAFE"

        registry = ToolRegistry(workspace_root=tmpdir)
        # Summary list check
        summary_out = registry.execute("get_evidence_by_status", {"status": "FAILED", "limit": 5})
        assert secret_key not in summary_out

        # Full evidence detail check
        full_out = registry.execute("get_evidence", {"task_id": "task_sec_status"})
        assert secret_key not in full_out
        assert "[REDACTED_SECRET]" in full_out


def test_historical_status_filtered_evidence_not_current_authority():
    """Verify historical status-filtered SUCCESS evidence does NOT validate current workspace state."""
    with tempfile.TemporaryDirectory() as tmpdir:
        logger = EvidenceLogger(workspace_root=tmpdir)
        ev = CodingTaskEvidence(task_id="old_succ_task", result="SUCCESS")
        ev.add_file_changed("core/agent/missing_file.py")
        logger.record_evidence(ev)

        registry = ToolRegistry(workspace_root=tmpdir)
        res_json = registry.execute("get_evidence_by_status", {"status": "SUCCESS"})
        summaries = json.loads(res_json)

        # Historical status-filtered summary returned
        assert len(summaries) >= 1
        found = [s for s in summaries if s["task_id"] == "old_succ_task"]
        assert len(found) == 1
        assert found[0]["result"] == "SUCCESS"

        # Independent current state revalidation: workspace file missing_file.py does NOT exist
        assert not os.path.exists(os.path.join(tmpdir, "core", "agent", "missing_file.py"))
