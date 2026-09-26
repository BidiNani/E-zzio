"""
tests/test_a14_capability_lab.py — Acceptance Test Suite for Phase A14 External Capability Laboratory.
Tests:
- PiG probe (adapter distinction, absent binary -> DEFERRED, fail-closed fallback)
- VoiceStudio probe (adapter distinction, unlistening server -> DEFERRED, failover verified)
- Zero dependency pollution in core kernel
- Never marks unavailable external capability as LIVE PROVEN
"""
import pytest

from core.capabilities.capability_lab import ExternalCapabilityLab


def test_a14_1_pig_probe_absent_binary_deferred(tmp_path):
    lab = ExternalCapabilityLab(workspace_root=str(tmp_path))
    res = lab.probe_pig(custom_binary="/invalid/pig/executable")

    # HARD INVARIANT: Absent binary must be DEFERRED, NEVER LIVE PROVEN
    assert res["status"] == "DEFERRED"
    assert res["binary_present"] is False
    assert res["adapter_valid"] is True
    assert res["fail_closed_fallback"] is True
    assert res["security_confined"] is True
    assert res["cancellation_verified"] is True
    assert "PiG binary not installed" in res["reason"]


def test_a14_2_voicestudio_probe_offline_server_deferred(tmp_path):
    lab = ExternalCapabilityLab(workspace_root=str(tmp_path))
    res = lab.probe_voicestudio(host="127.0.0.1", port=39997)

    # HARD INVARIANT: Offline server must be DEFERRED, NEVER LIVE PROVEN
    assert res["status"] == "DEFERRED"
    assert res["server_reachable"] is False
    assert res["adapter_valid"] is True
    assert res["failover_verified"] is True
    assert res["fallback_to_text"] is True
    assert "server not running" in res["reason"]


def test_a14_3_zero_kernel_dependency_pollution(tmp_path):
    lab = ExternalCapabilityLab(workspace_root=str(tmp_path))
    res = lab.verify_zero_kernel_pollution()

    # Core kernel must operate cleanly without torch, whisper, or torchaudio
    assert res["clean_kernel"] is True
    assert len(res["polluting_modules_found"]) == 0
    assert res["status"] == "PROVEN"


def test_a14_4_never_fake_proven_invariant(tmp_path):
    lab = ExternalCapabilityLab(workspace_root=str(tmp_path))
    pig_res = lab.probe_pig(custom_binary="/invalid/pig")
    vs_res = lab.probe_voicestudio(port=39996)

    # Both must explicitly NOT be LIVE PROVEN
    assert pig_res["status"] != "LIVE PROVEN"
    assert vs_res["status"] != "LIVE PROVEN"
