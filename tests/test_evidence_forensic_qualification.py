"""Comprehensive forensic qualification test suite for get_evidence and list_evidences (Mission 11)."""

import json
import os
import tempfile

from core.agent.agent_guard import AgentPolicyGuard
from core.agent.evidence_logger import CodingTaskEvidence, EvidenceLogger
from core.agent.tools_registry import ToolRegistry


def test_objective_a_tool_access():
    """OBJECTIF A — Tool registration, execution, and policy guard governance."""
    with tempfile.TemporaryDirectory() as tmpdir:
        registry = ToolRegistry(workspace_root=tmpdir)
        tools = registry.list_tools()
        names = [t.get("name") for t in tools]

        assert "get_evidence" in names
        assert "list_evidences" in names

        guard = AgentPolicyGuard(workspace_root=tmpdir)
        cls_get, _ = guard.classify_action("get_evidence", {"task_id": "test_1"})
        cls_list, _ = guard.classify_action("list_evidences", {"limit": 5})

        assert cls_get == "SAFE"
        assert cls_list == "SAFE"


def test_objective_b_task_isolation_and_path_traversal():
    """OBJECTIF B — Task isolation & path traversal rejection."""
    with tempfile.TemporaryDirectory() as tmpdir:
        logger = EvidenceLogger(workspace_root=tmpdir)

        # Record legitimate evidence
        ev = CodingTaskEvidence(task_id="task_isolated_001", plan="Isolation test")
        logger.record_evidence(ev)

        # Test valid task_id
        assert logger.get_evidence("task_isolated_001") is not None

        # Test path traversal attempts
        assert logger.get_evidence("../../secrets/vault") is None
        assert logger.get_evidence("..\\..\\config\\secret") is None
        assert logger.get_evidence("../task_isolated_001") is None
        assert logger.get_evidence("/etc/passwd") is None

        # Test invalid task_id types via registry
        registry = ToolRegistry(workspace_root=tmpdir)
        assert "[INVALID_ARGUMENTS]" in registry.execute("get_evidence", {"task_id": ""})
        assert "[INVALID_ARGUMENTS]" in registry.execute("get_evidence", {"task_id": None})
        assert "[INVALID_ARGUMENTS]" in registry.execute("get_evidence", {"task_id": 123})
        assert "[NOT_FOUND]" in registry.execute("get_evidence", {"task_id": "../../secrets/vault"})


def test_objective_c_confidentiality_redaction():
    """OBJECTIF C & C2 — Synthetic secret redaction on storage and retrieval."""
    with tempfile.TemporaryDirectory() as tmpdir:
        logger = EvidenceLogger(workspace_root=tmpdir)
        ev = CodingTaskEvidence(task_id="task_secret_test", plan="Secret test")

        # Add synthetic secrets matching SECRET_PATTERNS
        secret_key_1 = "AIzaSyB1234567890abcdefghijklmnopqrstuv"
        secret_key_2 = "gsk_12345678901234567890123456789012"

        ev.add_command_result(f"curl -H 'Authorization: {secret_key_1}' https://api.com", 0, 100)
        ev.final_diff = f"diff --git a/app.py\n+api_key = '{secret_key_2}'"
        logger.record_evidence(ev)

        registry = ToolRegistry(workspace_root=tmpdir)
        res = registry.execute("get_evidence", {"task_id": "task_secret_test"})

        assert secret_key_1 not in res
        assert secret_key_2 not in res
        assert "[REDACTED_SECRET]" in res


def test_objective_d_limit_bounding_and_ordering():
    """OBJECTIF D & D2 — Limit normalization, bounding (max 100), and ordering."""
    with tempfile.TemporaryDirectory() as tmpdir:
        logger = EvidenceLogger(workspace_root=tmpdir)

        for i in range(15):
            ev = CodingTaskEvidence(task_id=f"task_{i:02d}", start_time=1000.0 + i)
            logger.record_evidence(ev)

        registry = ToolRegistry(workspace_root=tmpdir)

        # Test default limit (10)
        res1 = json.loads(registry.execute("list_evidences", {}))
        assert len(res1) == 10
        # Ordered by start_time descending (task_14 newest)
        assert res1[0]["task_id"] == "task_14"
        assert res1[9]["task_id"] == "task_05"

        # Test edge case limits: None, string "5", negative -1, zero 0, huge limit 1000
        res_none = json.loads(registry.execute("list_evidences", {"limit": None}))
        assert len(res_none) == 10

        res_str = json.loads(registry.execute("list_evidences", {"limit": "3"}))
        assert len(res_str) == 3

        res_neg = json.loads(registry.execute("list_evidences", {"limit": -5}))
        assert len(res_neg) == 10  # Normalized to safe default

        res_zero = json.loads(registry.execute("list_evidences", {"limit": 0}))
        assert len(res_zero) == 10  # Normalized to safe default


def test_objective_e_read_only_guarantee():
    """OBJECTIF E — Read-only guarantee: zero workspace modification."""
    with tempfile.TemporaryDirectory() as tmpdir:
        logger = EvidenceLogger(workspace_root=tmpdir)
        ev = CodingTaskEvidence(task_id="task_ro_check", start_time=500.0)
        logger.record_evidence(ev)

        evidence_dir = logger.evidence_dir
        initial_files = os.listdir(evidence_dir)
        initial_timestamps = {f: os.path.getmtime(os.path.join(evidence_dir, f)) for f in initial_files}

        registry = ToolRegistry(workspace_root=tmpdir)
        registry.execute("get_evidence", {"task_id": "task_ro_check"})
        registry.execute("list_evidences", {"limit": 10})

        current_files = os.listdir(evidence_dir)
        current_timestamps = {f: os.path.getmtime(os.path.join(evidence_dir, f)) for f in current_files}

        assert initial_files == current_files
        assert initial_timestamps == current_timestamps


def test_objective_f_integrity_and_corruption_handling():
    """OBJECTIF F & F2 — Integrity verification & corrupt file handling."""
    with tempfile.TemporaryDirectory() as tmpdir:
        logger = EvidenceLogger(workspace_root=tmpdir)

        # 1. Non-existent task
        assert logger.get_evidence("task_does_not_exist") is None

        # 2. Corrupt JSON file
        corrupt_file = os.path.join(logger.evidence_dir, "task_corrupt_evidence.json")
        with open(corrupt_file, "w", encoding="utf-8") as f:
            f.write("{ INVALID JSON CONTENT ...")

        assert logger.get_evidence("task_corrupt") is None

        # list_evidences should gracefully ignore corrupt file
        ev = CodingTaskEvidence(task_id="task_valid_one", start_time=100.0)
        logger.record_evidence(ev)

        summaries = logger.list_evidences(limit=10)
        assert len(summaries) == 1
        assert summaries[0]["task_id"] == "task_valid_one"


def test_objective_g_historical_state_not_current_authority():
    """OBJECTIF G & 21 — Historical evidence != current state authority."""
    with tempfile.TemporaryDirectory() as tmpdir:
        logger = EvidenceLogger(workspace_root=tmpdir)
        ev = CodingTaskEvidence(task_id="old_mission_success", result="SUCCESS")
        ev.add_file_changed("core/agent/old_file.py")
        logger.record_evidence(ev)

        # Read historical evidence
        fetched = logger.get_evidence("old_mission_success")
        assert fetched["result"] == "SUCCESS"

        # Verify that workspace file core/agent/old_file.py does NOT exist
        assert not os.path.exists(os.path.join(tmpdir, "core", "agent", "old_file.py"))


def test_objective_h_auditability():
    """OBJECTIF H — Execution audit logging in tool_executions.jsonl."""
    with tempfile.TemporaryDirectory() as tmpdir:
        logger = EvidenceLogger(workspace_root=tmpdir)
        ev = CodingTaskEvidence(task_id="task_audit_test", result="SUCCESS")
        logger.record_evidence(ev)

        registry = ToolRegistry(workspace_root=tmpdir)
        registry.execute("get_evidence", {"task_id": "task_audit_test"})
        registry.execute("list_evidences", {"limit": 5})

        audit_file = os.path.join(tmpdir, "state", "audit", "tool_executions.jsonl")
        assert os.path.exists(audit_file)

        with open(audit_file, encoding="utf-8") as f:
            lines = [json.loads(line) for line in f if line.strip()]

        tools_logged = [entry["tool"] for entry in lines]
        assert "get_evidence" in tools_logged
        assert "list_evidences" in tools_logged
