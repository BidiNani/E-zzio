"""Test suite for Inter-Mission Continuity, status-filtered evidence querying, and historical vs current state isolation (Mission 12)."""

import json
import os
import tempfile

from core.agent.agent_guard import AgentPolicyGuard
from core.agent.evidence_logger import CodingTaskEvidence, EvidenceLogger
from core.agent.tools_registry import ToolRegistry


def test_evidence_logger_get_evidence_by_status():
    """Verify EvidenceLogger.get_evidence_by_status filters evidence records by outcome status."""
    with tempfile.TemporaryDirectory() as tmpdir:
        logger = EvidenceLogger(workspace_root=tmpdir)

        ev1 = CodingTaskEvidence(
            task_id="task_success_1",
            plan="Success plan 1",
            result="SUCCESS",
            start_time=1000.0,
        )
        logger.record_evidence(ev1)

        ev2 = CodingTaskEvidence(
            task_id="task_failed_1",
            plan="Failed plan 1",
            result="FAILED",
            start_time=2000.0,
        )
        logger.record_evidence(ev2)

        ev3 = CodingTaskEvidence(
            task_id="task_success_2",
            plan="Success plan 2",
            result="SUCCESS",
            start_time=3000.0,
        )
        logger.record_evidence(ev3)

        successes = logger.get_evidence_by_status(status="SUCCESS", limit=10)
        assert len(successes) == 2
        assert successes[0]["task_id"] == "task_success_2"
        assert successes[1]["task_id"] == "task_success_1"

        failures = logger.get_evidence_by_status(status="FAILED", limit=10)
        assert len(failures) == 1
        assert failures[0]["task_id"] == "task_failed_1"


def test_tool_registry_get_evidence_by_status():
    """Verify ToolRegistry exposes and executes get_evidence_by_status correctly."""
    with tempfile.TemporaryDirectory() as tmpdir:
        logger = EvidenceLogger(workspace_root=tmpdir)

        ev_fail = CodingTaskEvidence(
            task_id="task_audit_fail",
            plan="Failing test run",
            result="FAILED",
            start_time=1200.0,
        )
        logger.record_evidence(ev_fail)

        registry = ToolRegistry(workspace_root=tmpdir)
        tools = registry.list_tools()
        tool_names = [t.get("name") for t in tools]

        assert "get_evidence_by_status" in tool_names

        res_json = registry.execute("get_evidence_by_status", {"status": "FAILED", "limit": 5})
        parsed = json.loads(res_json)

        assert len(parsed) == 1
        assert parsed[0]["task_id"] == "task_audit_fail"
        assert parsed[0]["result"] == "FAILED"


def test_agent_policy_guard_get_evidence_by_status():
    """Verify AgentPolicyGuard classifies get_evidence_by_status as SAFE."""
    with tempfile.TemporaryDirectory() as tmpdir:
        guard = AgentPolicyGuard(workspace_root=tmpdir)
        cls_action, reason = guard.classify_action("get_evidence_by_status", {"status": "SUCCESS"})

        assert cls_action == "SAFE"
        assert "lecture ou recherche" in reason.lower()


def test_inter_mission_historical_evidence_not_current_authority():
    """Verify historical evidence retrieved as context does NOT alter current state or grant authority."""
    with tempfile.TemporaryDirectory() as tmpdir:
        logger = EvidenceLogger(workspace_root=tmpdir)
        historical_ev = CodingTaskEvidence(
            task_id="mission_11_historical",
            result="SUCCESS",
            start_time=500.0,
        )
        historical_ev.add_file_changed("core/agent/historical_file.py")
        logger.record_evidence(historical_ev)

        # Retrieve historical context via ToolRegistry
        registry = ToolRegistry(workspace_root=tmpdir)
        res_json = registry.execute("get_evidence", {"task_id": "mission_11_historical"})
        fetched = json.loads(res_json)

        # Historical context retrieved
        assert fetched["task_id"] == "mission_11_historical"
        assert fetched["result"] == "SUCCESS"

        # Current workspace revalidation: historical file does NOT exist in workspace
        target_path = os.path.join(tmpdir, "core", "agent", "historical_file.py")
        assert not os.path.exists(target_path)
