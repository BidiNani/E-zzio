"""tests/test_run_test_file_boundary.py — Regression test for run_test_file workspace boundary enforcement."""
import os

import pytest

from core.agent.agent_guard import AgentPolicyGuard
from core.agent.tools_registry import ToolRegistry


def test_agent_guard_run_test_file_boundary_denial():
    guard = AgentPolicyGuard(r"G:\AI\E-zzio")

    # 1. Path traversal attempt outside workspace
    allowed, reason = guard.evaluate_intent("run_test_file", {"test_path": "../../outside_test.py"})
    assert allowed is False, f"Expected boundary denial, but allowed with reason: {reason}"
    assert "[SECURITY DENY]" in reason or "workspace" in reason.lower()

    # 2. Authorized path inside workspace
    allowed_valid, reason_valid = guard.evaluate_intent("run_test_file", {"test_path": "tests/test_e2e_probe_target.py"})
    assert allowed_valid is True, f"Expected allow for valid path, but got: {reason_valid}"


def test_tools_registry_run_test_file_boundary_interception():
    registry = ToolRegistry(r"G:\AI\E-zzio")

    res = registry.execute_tool("run_test_file", {"test_path": "../../outside_test.py"})
    assert "[RUNTIME POLICY BLOCKED]" in res or "[SECURITY DENY]" in res
