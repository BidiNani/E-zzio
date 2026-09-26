"""Test suite for EvidenceLogger list_evidences and ToolRegistry evidence querying tools."""

import json
import os
import tempfile

from core.agent.agent_guard import AgentPolicyGuard
from core.agent.evidence_logger import CodingTaskEvidence, EvidenceLogger
from core.agent.tools_registry import ToolRegistry


def test_evidence_logger_list_evidences():
    """Verify EvidenceLogger.list_evidences scans, parses and ranks evidence files."""
    with tempfile.TemporaryDirectory() as tmpdir:
        logger = EvidenceLogger(workspace_root=tmpdir)

        ev1 = CodingTaskEvidence(
            task_id="task_alpha",
            plan="First test task",
            result="SUCCESS",
            provider="test_provider",
            model_used="model_a",
            start_time=1000.0,
        )
        ev1.add_file_changed("core/agent/file_a.py")
        ev1.add_command_result("pytest", 0, 150)
        ev1.add_test_result("test_a", True, "Passed")
        logger.record_evidence(ev1)

        ev2 = CodingTaskEvidence(
            task_id="task_beta",
            plan="Second test task",
            result="FAILED",
            provider="test_provider",
            model_used="model_b",
            start_time=2000.0,
        )
        ev2.add_file_changed("core/agent/file_b.py")
        ev2.add_file_changed("core/agent/file_c.py")
        logger.record_evidence(ev2)

        summaries = logger.list_evidences(limit=10)
        assert len(summaries) == 2
        # Most recent first (start_time 2000.0 > 1000.0)
        assert summaries[0]["task_id"] == "task_beta"
        assert summaries[0]["result"] == "FAILED"
        assert summaries[0]["files_changed_count"] == 2

        assert summaries[1]["task_id"] == "task_alpha"
        assert summaries[1]["result"] == "SUCCESS"
        assert summaries[1]["files_changed_count"] == 1
        assert summaries[1]["commands_count"] == 1
        assert summaries[1]["tests_count"] == 1


def test_tool_registry_evidence_tools():
    """Verify ToolRegistry exposes and executes get_evidence and list_evidences."""
    with tempfile.TemporaryDirectory() as tmpdir:
        logger = EvidenceLogger(workspace_root=tmpdir)
        ev = CodingTaskEvidence(
            task_id="task_gamma",
            plan="Gamma task plan",
            result="SUCCESS",
            start_time=1500.0,
        )
        ev.add_file_changed("core/agent/evidence_logger.py")
        logger.record_evidence(ev)

        registry = ToolRegistry(workspace_root=tmpdir)
        tools = registry.list_tools()
        tool_names = [t.get("name") for t in tools]

        assert "get_evidence" in tool_names
        assert "list_evidences" in tool_names

        # Execute get_evidence
        res_get = registry.execute("get_evidence", {"task_id": "task_gamma"})
        parsed_get = json.loads(res_get)
        assert parsed_get["task_id"] == "task_gamma"
        assert parsed_get["result"] == "SUCCESS"

        # Execute get_evidence with non-existent task
        res_missing = registry.execute("get_evidence", {"task_id": "task_missing"})
        assert "[NOT_FOUND]" in res_missing

        # Execute list_evidences
        res_list = registry.execute("list_evidences", {"limit": 5})
        parsed_list = json.loads(res_list)
        assert len(parsed_list) == 1
        assert parsed_list[0]["task_id"] == "task_gamma"


def test_agent_policy_guard_evidence_tools():
    """Verify AgentPolicyGuard classifies evidence tools as SAFE."""
    with tempfile.TemporaryDirectory() as tmpdir:
        guard = AgentPolicyGuard(workspace_root=tmpdir)

        cls_get, reason_get = guard.classify_action("get_evidence", {"task_id": "task_123"})
        assert cls_get == "SAFE"

        cls_list, reason_list = guard.classify_action("list_evidences", {"limit": 10})
        assert cls_list == "SAFE"
