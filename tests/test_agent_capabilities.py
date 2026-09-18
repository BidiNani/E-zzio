"""
tests/test_agent_capabilities.py — Security & Functional Unit tests for Capability Profiles & Autonomous Preflight Manager
"""
import sys

import pytest

from core.agent.capability_manager import CapabilityManager, capability_manager


def test_capability_profile_mapping():
    mgr = CapabilityManager()

    coding = mgr.get_profile("CODING")
    assert coding.role == "CODING"
    assert "filesystem" in coding.tools
    assert "pytest" in coding.dependencies

    forensic = mgr.get_profile("FORENSIC")
    assert forensic.role == "FORENSIC"
    assert "grep" in forensic.tools

    voice = mgr.get_profile("VOICE")
    assert voice.role == "VOICE"
    assert "stt" in voice.tools

def test_preflight_check():
    mgr = CapabilityManager()

    # Preflight check pour le rôle CODING
    res = mgr.preflight_check("CODING", auto_install=False)
    assert res["role"] == "CODING"
    assert "tools" in res
    assert "status" in res
    assert res["ready"] is True

def test_dependency_check_and_whitelist_security():
    mgr = CapabilityManager()
    assert mgr.check_dependency("sys") is True
    assert mgr.check_dependency("os") is True
    assert mgr.check_dependency("non_existent_fake_module_xyz99") is False

    # Sécurité anti-injection : refus d'installation pour les paquets hors whitelist
    assert mgr.auto_install_dependency("malicious_unwhitelisted_package_xyz99") is False

def test_external_tool_distinction():
    mgr = CapabilityManager()
    # Distinction entre outil externe système et dépendance Python
    assert mgr.check_external_tool("python") is True
    assert mgr.python_bin == sys.executable

if __name__ == "__main__":
    test_capability_profile_mapping()
    test_preflight_check()
    test_dependency_check_and_whitelist_security()
    test_external_tool_distinction()
    print("✅ ALL CAPABILITY MANAGER SECURITY & FUNCTIONAL TESTS PASSED")
