"""
tests/test_a12_workspace_intelligence.py — Acceptance Test Suite for Phase A12 Workspace Intelligence.
Tests:
- read-only verification (no files created or modified by scan)
- workspace confinement (blocks outside paths)
- deterministic output
- large / restricted path handling
- real repository scan
- test intelligence ('detected' is never 'passed')
- context package generation
"""
import os

import pytest

from core.workspace.workspace_intel import WorkspaceIntelligence


def test_a12_1_read_only_scan_invariance(tmp_path):
    # Setup test workspace fixture
    f1 = tmp_path / "main.py"
    f1.write_text("print('hello')", encoding="utf-8")
    f2 = tmp_path / "test_sample.py"
    f2.write_text("def test_one(): pass", encoding="utf-8")
    f3 = tmp_path / "pyproject.toml"
    f3.write_text("[project]\nname='demo'\n", encoding="utf-8")

    initial_files = set(os.listdir(tmp_path))
    mtimes_before = {f: os.path.getmtime(tmp_path / f) for f in initial_files}

    scanner = WorkspaceIntelligence(workspace_root=str(tmp_path))
    results = scanner.scan()

    # Verify no files were added or modified
    assert set(os.listdir(tmp_path)) == initial_files
    for f in initial_files:
        assert os.path.getmtime(tmp_path / f) == mtimes_before[f]

    assert results["languages"]["Python"] == 2
    assert "pyproject.toml" in results["dependencies"]
    assert results["tests"]["test_file_count"] == 1
    assert "pytest" in results["tests"]["runner_commands"]


def test_a12_2_confinement_blocks_outside_paths(tmp_path):
    ws = tmp_path / "authorized_ws"
    ws.mkdir()
    outside = tmp_path / "secret_outside"
    outside.mkdir()
    (outside / "leak.py").write_text("secret = 123", encoding="utf-8")

    scanner = WorkspaceIntelligence(workspace_root=str(ws))
    assert scanner._is_within_workspace(str(outside / "leak.py")) is False
    assert scanner._is_within_workspace("C:\\Windows\\System32\\calc.exe") is False
    assert scanner._is_within_workspace(str(ws / "file.py")) is True


def test_a12_3_deterministic_manifest_output(tmp_path):
    (tmp_path / "app.py").write_text("# entry", encoding="utf-8")
    (tmp_path / "requirements.txt").write_text("pytest\n", encoding="utf-8")

    scanner = WorkspaceIntelligence(workspace_root=str(tmp_path))
    scan1 = scanner.scan()
    scan2 = scanner.scan()

    assert scan1["languages"] == scan2["languages"]
    assert scan1["dependencies"] == scan2["dependencies"]
    assert scan1["entrypoints"] == scan2["entrypoints"]

    manifest_file = tmp_path / "workspace_manifest.json"
    scanner.generate_manifest(output_path=str(manifest_file))
    assert manifest_file.exists()


def test_a12_4_large_file_and_ignored_path_handling(tmp_path):
    # Create an ignored dir and a large file
    pycache = tmp_path / "__pycache__"
    pycache.mkdir()
    (pycache / "compiled.pyc").write_text("data", encoding="utf-8")

    large_f = tmp_path / "big_dataset.bin"
    # Create 2KB file and set threshold to 1KB to test detection
    large_f.write_bytes(b"x" * 2048)

    scanner = WorkspaceIntelligence(workspace_root=str(tmp_path))
    scan = scanner.scan(max_file_size_bytes=1024)

    assert "big_dataset.bin" in scan["large_files"]
    assert scan["ignored_paths_count"] >= 1


def test_a12_5_test_detected_never_claims_passed(tmp_path):
    (tmp_path / "test_demo.py").write_text("def test_x(): assert False", encoding="utf-8")
    scanner = WorkspaceIntelligence(workspace_root=str(tmp_path))
    scan = scanner.scan()

    # HARD INVARIANT: Detected tests are NEVER marked as passed by static scanner
    assert scan["tests"]["test_suite_detected"] is True
    assert scan["tests"]["status"] == "DETECTED_NOT_RUN"
    assert scan["tests"]["status"] != "PASSED"


def test_a12_6_context_package_structure(tmp_path):
    (tmp_path / "agent_guard.py").write_text("class PolicyGuard: pass", encoding="utf-8")
    scanner = WorkspaceIntelligence(workspace_root=str(tmp_path))
    pkg = scanner.build_context_package()

    assert "workspace_context" in pkg
    assert "project_map" in pkg
    assert "test_map" in pkg
    assert "risk_summary" in pkg
    assert pkg["risk_summary"]["critical_paths_count"] >= 1
