"""
tests/test_a9_forensic_observatory.py — Acceptance Test Suite for Phase A9 Forensic Observatory.
Covers:
- A9.1 ezzio doctor
- A9.2 ezzio verify
- A9.3 evidence bundle (10 JSON artifacts)
- A9.4 capability detector (PiG & VoiceStudio distinction)
- A9.5 regression manifest
- CLI invocation
"""
import os
import sys

import pytest

from core.observability.capability_detector import CapabilityDetector
from core.observability.doctor import EzzioDoctor
from core.observability.evidence_bundle import EvidenceBundleBuilder
from core.observability.regression_manifest import RegressionManifestGenerator
from core.observability.verify import EzzioVerifier


def test_a9_1_ezzio_doctor_diagnostics(tmp_path):
    doctor = EzzioDoctor(workspace_root=str(tmp_path))
    results = doctor.diagnose()

    expected_keys = [
        "GIT", "PYTHON", "VENV", "CONFIG", "DATABASES", "MISSION_STORE",
        "AUDIT_LEDGER", "MODEL_REGISTRY", "MODEL_ROUTER", "PROVIDER_FACTORY",
        "PROVIDER_HEALTH", "OLLAMA", "CPU_POLICY", "OPTIONAL_PIG",
        "OPTIONAL_VOICESTUDIO", "DISK", "MEMORY", "PORTS", "TEST_DISCOVERY",
        "WORKSPACE",
    ]
    for key in expected_keys:
        assert key in results, f"Missing diagnostic key: {key}"
        assert results[key]["status"] in (
            "PROVEN", "MEASURED", "OBSERVED", "PARTIAL", "UNKNOWN", "DEFERRED", "BLOCKED"
        )

    report_str = doctor.format_report()
    assert "E-ZZIO DOCTOR" in report_str
    assert "WORKSPACE" in report_str


def test_a9_2_ezzio_verify_read_only_invariants(tmp_path):
    verifier = EzzioVerifier(workspace_root=str(tmp_path))
    results = verifier.verify_all()

    expected_invariants = [
        "ARCHITECTURE", "ROUTING_AUTHORITY", "POLICY", "BUDGET",
        "MISSION_PERSISTENCE", "CHECKPOINTING", "RECOVERY",
        "SELF_CORRECTION", "VALIDATION_GATES", "AUDIT_INTEGRITY",
        "EXTERNAL_CONTRACTS",
    ]
    for inv in expected_invariants:
        assert inv in results, f"Missing verification invariant: {inv}"
        assert results[inv]["status"] == "PROVEN", f"Invariant {inv} failed: {results[inv]}"


def test_a9_3_evidence_bundle_generation(tmp_path):
    builder = EvidenceBundleBuilder(workspace_root=str(tmp_path))
    m_id = "mission-a9-test-01"

    paths = builder.create_bundle(
        mission_id=m_id,
        mission_data={"goal": "Forensic proof", "status": "COMPLETED"},
        timeline=[{"timestamp": 123.45, "event": "start"}],
        decisions=[{"decision": "LOCAL", "confidence": 1.0}],
        checkpoints=[{"step": 1, "status": "COMPLETED"}],
        validation={"verified": True, "evidence_type": "EMPIRICAL_PROOF"},
        audit_refs=["audit-ref-001"],
        changed_files=["utils.py"],
        tests={"tests_run": 5, "tests_passed": 5},
        final_status="COMPLETED",
    )

    required_artifacts = [
        "mission.json", "timeline.json", "decisions.json", "checkpoints.json",
        "validation.json", "audit_refs.json", "changed_files.json", "tests.json",
        "environment.json", "final.json",
    ]
    assert len(paths) == 10
    for artifact in required_artifacts:
        assert artifact in paths
        assert os.path.exists(paths[artifact])
        assert os.path.getsize(paths[artifact]) > 0


def test_a9_4_capability_detector_distinction(tmp_path):
    detector = CapabilityDetector(workspace_root=str(tmp_path))

    # PiG with nonexistent binary must be DEFERRED
    pig_stat = detector.detect_pig(custom_path="/invalid/pig/path")
    assert pig_stat.status == "DEFERRED"
    assert pig_stat.service_available is False
    assert pig_stat.executable is False

    # VoiceStudio with unlistening port must be DEFERRED
    vs_stat = detector.detect_voicestudio(port=39998)
    assert vs_stat.status == "DEFERRED"
    assert vs_stat.service_available is False

    # Never marks unavailable capability as PROVEN
    assert pig_stat.status != "PROVEN"
    assert vs_stat.status != "PROVEN"


def test_a9_5_regression_manifest(tmp_path):
    gen = RegressionManifestGenerator(workspace_root=str(tmp_path))
    manifest_path = gen.save_manifest(
        filepath=str(tmp_path / "runtime" / "manifest.json"),
        test_summary={"tests_passed": 10, "tests_failed": 0},
    )
    assert os.path.exists(manifest_path)

    import json
    with open(manifest_path, encoding="utf-8") as f:
        data = json.load(f)

    assert "git" in data
    assert "environment" in data
    assert "capabilities" in data
    assert "proof_statuses" in data
    assert data["test_summary"]["tests_passed"] == 10


def test_a9_6_cli_doctor_and_verify(capsys):
    import subprocess
    # Run ezzio_cli.py --doctor and --verify as subcommands
    p_doc = subprocess.run([sys.executable, "ezzio_cli.py", "--doctor"], capture_output=True, text=True)
    assert p_doc.returncode == 0
    assert "E-ZZIO DOCTOR" in p_doc.stdout

    p_ver = subprocess.run([sys.executable, "ezzio_cli.py", "--verify"], capture_output=True, text=True)
    assert p_ver.returncode == 0
    assert "E-ZZIO VERIFY" in p_ver.stdout
