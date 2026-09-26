"""Forensic Trust-Boundary Qualification Test Suite for capability_manager.py."""

import pytest

from core.agent.capability_manager import (
    ALLOWED_DEPENDENCY_WHITELIST,
    CapabilityManager,
    register_allowed_dependency,
)


def test_register_allowed_dependency_input_validation():
    """Gate D & E: Verify input validation and fail-closed handling in register_allowed_dependency."""
    initial_size = len(ALLOWED_DEPENDENCY_WHITELIST)

    # Valid string
    assert register_allowed_dependency("valid_test_pkg_1") is True
    assert "valid_test_pkg_1" in ALLOWED_DEPENDENCY_WHITELIST

    # Idempotence (Gate F)
    assert register_allowed_dependency("valid_test_pkg_1") is True

    # Invalid / Malformed / Non-string / Empty inputs (Gate D, E)
    assert register_allowed_dependency(None) is False
    assert register_allowed_dependency("") is False
    assert register_allowed_dependency("   ") is False
    assert register_allowed_dependency(123) is False
    assert register_allowed_dependency(["pkg"]) is False
    assert register_allowed_dependency("--invalid-flag") is False
    assert register_allowed_dependency("pkg; rm -rf /") is False
    assert register_allowed_dependency("pkg with spaces") is False

    # Cleanup test additions
    ALLOWED_DEPENDENCY_WHITELIST.discard("valid_test_pkg_1")


def test_preflight_check_four_state_boolean_matrix(monkeypatch):
    """Gate J & K: Verify preflight_check 4-state boolean matrix and tool/dependency separation."""
    mgr = CapabilityManager()

    # Case 1: deps_ok = True, tools_ok = True -> ready = True
    monkeypatch.setattr(mgr, "check_dependency", lambda dep: True)
    monkeypatch.setattr(mgr, "check_external_tool", lambda tool: True)
    res_1 = mgr.preflight_check("CODING", auto_install=False)
    assert res_1["ready"] is True
    assert res_1["status"] == "READY"
    assert len(res_1["missing_deps"]) == 0
    assert len(res_1["missing_tools"]) == 0

    # Case 2: deps_ok = False, tools_ok = True -> ready = False
    monkeypatch.setattr(mgr, "check_dependency", lambda dep: False)
    monkeypatch.setattr(mgr, "check_external_tool", lambda tool: True)
    res_2 = mgr.preflight_check("CODING", auto_install=False)
    assert res_2["ready"] is False
    assert res_2["status"] == "BLOCKED"
    assert len(res_2["missing_deps"]) > 0

    # Case 3: deps_ok = True, tools_ok = False -> ready = False
    monkeypatch.setattr(mgr, "check_dependency", lambda dep: True)
    monkeypatch.setattr(mgr, "check_external_tool", lambda tool: False)
    res_3 = mgr.preflight_check("CODING", auto_install=False)
    assert res_3["ready"] is False
    assert res_3["status"] == "BLOCKED"
    assert len(res_3["missing_tools"]) > 0

    # Case 4: deps_ok = False, tools_ok = False -> ready = False
    monkeypatch.setattr(mgr, "check_dependency", lambda dep: False)
    monkeypatch.setattr(mgr, "check_external_tool", lambda tool: False)
    res_4 = mgr.preflight_check("CODING", auto_install=False)
    assert res_4["ready"] is False
    assert res_4["status"] == "BLOCKED"
    assert len(res_4["missing_deps"]) > 0
    assert len(res_4["missing_tools"]) > 0

    # Gate K: Disjoint check available_tools vs missing_tools
    avail_set = set(res_4["available_tools"])
    miss_set = set(res_4["missing_tools"])
    assert avail_set.intersection(miss_set) == set()
