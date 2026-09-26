"""Test capability manager preflight tool verification and dependency whitelist registration."""

import tempfile

from core.agent.capability_manager import CapabilityManager, register_allowed_dependency
from core.agent.evidence_logger import CodingTaskEvidence, EvidenceLogger


def test_preflight_check_tool_verification():
    """Verify preflight_check inspects external tool availability."""
    mgr = CapabilityManager()

    # Preflight for CODING role
    result = mgr.preflight_check("CODING", auto_install=False)
    assert "available_tools" in result
    assert "missing_tools" in result
    assert "git" in result["available_tools"] or "git" in result["missing_tools"]
    assert isinstance(result["ready"], bool)


def test_register_allowed_dependency():
    """Verify register_allowed_dependency allows extending the dependency whitelist."""
    mgr = CapabilityManager()

    # Attempting un-whitelisted package should fail
    assert mgr.auto_install_dependency("untrusted_fake_pkg_xyz") is False

    # Registering package
    register_allowed_dependency("custom_tool_dep")
    from core.agent.capability_manager import ALLOWED_DEPENDENCY_WHITELIST
    assert "custom_tool_dep" in ALLOWED_DEPENDENCY_WHITELIST


def test_evidence_verification_end_to_end():
    """Verify evidence logging and retrieval coherence for capability preflight task."""
    with tempfile.TemporaryDirectory() as tmpdir:
        logger = EvidenceLogger(workspace_root=tmpdir)
        evidence = CodingTaskEvidence(task_id="task_cap_mgr_008", plan="Capability Manager Preflight Verification")

        evidence.add_file_changed("core/agent/capability_manager.py")
        evidence.add_command_result("pytest tests/test_capability_manager_enhancements.py", exit_code=0, duration_ms=150)
        evidence.add_test_result("test_preflight_check_tool_verification", passed=True, summary="1 passed")
        evidence.complete(result="SUCCESS", final_diff="--- diff core/agent/capability_manager.py ---")

        logger.record_evidence(evidence)

        loaded = logger.get_evidence("task_cap_mgr_008")
        assert loaded is not None
        assert loaded["task_id"] == "task_cap_mgr_008"
        assert loaded["result"] == "SUCCESS"
        assert "core/agent/capability_manager.py" in loaded["files_changed"]
        assert loaded["commands"][0]["exit_code"] == 0
