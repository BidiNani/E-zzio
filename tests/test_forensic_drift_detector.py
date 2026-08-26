"""
Adversarial and functional test suite for ForensicDriftDetector v1.
Strictly validates fail-closed behavior, reconciliation, and read-only guarantees.
"""

import json
import pytest
from pathlib import Path
from core.knowledge.drift_detector import ForensicDriftDetector, DriftVerdict, FileDriftStatus

@pytest.fixture
def detector():
    return ForensicDriftDetector()

def test_detector_initialization(detector):
    assert detector.root_dir.exists()
    assert detector.knowledge_dir.exists()
    assert detector.load_knowledge_map() is True

def test_detector_read_only_guarantee(detector):
    forbidden_prefixes = ("write", "delete", "remove", "update", "exec", "modify", "save", "patch", "heal", "fix", "clean")
    methods = [attr for attr in dir(detector) if not attr.startswith("_")]
    for m in methods:
        for prefix in forbidden_prefixes:
            assert not m.startswith(prefix), f"Forbidden mutating method detected: {m}"

def test_detector_drift_detection_structure(detector):
    res = detector.detect_drift(write_artifacts=False)
    assert res.verdict in (DriftVerdict.NO_DRIFT, DriftVerdict.DRIFT_DETECTED)
    assert res.reconciliation["all_reconciliations_passed"] is True
    assert res.metrics["physical_files_examined"] > 1000
    assert res.metrics["knowledge_map_files"] > 1000

def test_detector_adversarial_missing_map(tmp_path):
    det = ForensicDriftDetector(root_dir=tmp_path, knowledge_dir=tmp_path / "non_existent_knowledge")
    res = det.detect_drift(write_artifacts=False)
    assert res.verdict in (DriftVerdict.MAP_STALE, DriftVerdict.CRITICAL_DRIFT)
    assert res.reconciliation["passed"] is False

def test_detector_adversarial_corrupt_json(tmp_path):
    bad_kdir = tmp_path / "corrupt_kdir"
    bad_kdir.mkdir()
    (bad_kdir / "FILE_MANIFEST.json").write_text("{corrupt_json_content...", encoding="utf-8")
    det = ForensicDriftDetector(root_dir=tmp_path, knowledge_dir=bad_kdir)
    res = det.detect_drift(write_artifacts=False)
    assert res.verdict in (DriftVerdict.CRITICAL_DRIFT, DriftVerdict.MAP_STALE)

def test_detector_adversarial_simulated_synthetic_drift(tmp_path):
    ws = tmp_path / "workspace"
    kdir = ws / "_forensic" / "knowledge"
    kdir.mkdir(parents=True)

    (ws / "file_a.py").write_text("print('A')", encoding="utf-8")
    (ws / "file_b.py").write_text("print('B')", encoding="utf-8")
    (ws / "file_to_delete.py").write_text("print('Delete me')", encoding="utf-8")

    import hashlib
    def get_h(p):
        return hashlib.sha256(p.read_bytes()).hexdigest()

    h_a = get_h(ws / "file_a.py")
    h_b = get_h(ws / "file_b.py")
    h_del = get_h(ws / "file_to_delete.py")

    manifest = {
        "file_a.py": {"path": "file_a.py", "size_bytes": 10, "category": "core_engine", "is_excluded": False},
        "file_b.py": {"path": "file_b.py", "size_bytes": 10, "category": "core_engine", "is_excluded": False},
        "file_to_delete.py": {"path": "file_to_delete.py", "size_bytes": 17, "category": "core_engine", "is_excluded": False},
        "_forensic/knowledge/FILE_MANIFEST.json": {"path": "_forensic/knowledge/FILE_MANIFEST.json", "size_bytes": 100, "is_excluded": True},
        "_forensic/knowledge/FILE_HASHES.json": {"path": "_forensic/knowledge/FILE_HASHES.json", "size_bytes": 100, "is_excluded": True},
        "_forensic/knowledge/SYMBOL_INDEX.json": {"path": "_forensic/knowledge/SYMBOL_INDEX.json", "size_bytes": 100, "is_excluded": True},
        "_forensic/knowledge/API_MAP.json": {"path": "_forensic/knowledge/API_MAP.json", "size_bytes": 100, "is_excluded": True},
        "_forensic/knowledge/DATABASE_MAP.json": {"path": "_forensic/knowledge/DATABASE_MAP.json", "size_bytes": 100, "is_excluded": True},
        "_forensic/knowledge/MASTER_KNOWLEDGE.json": {"path": "_forensic/knowledge/MASTER_KNOWLEDGE.json", "size_bytes": 100, "is_excluded": True},
    }
    hashes = {
        "file_a.py": h_a,
        "file_b.py": h_b,
        "file_to_delete.py": h_del,
        "_forensic/knowledge/FILE_MANIFEST.json": "000",
        "_forensic/knowledge/FILE_HASHES.json": "000",
        "_forensic/knowledge/SYMBOL_INDEX.json": "000",
        "_forensic/knowledge/API_MAP.json": "000",
        "_forensic/knowledge/DATABASE_MAP.json": "000",
        "_forensic/knowledge/MASTER_KNOWLEDGE.json": "000",
    }
    symbols = {"classes": {}, "functions": {}}
    apis = {"http_routes": [], "websocket_routes": []}
    dbs = {"databases": {}}
    master = {"metrics": {"physical_files_count": 9}}

    (kdir / "FILE_MANIFEST.json").write_text(json.dumps(manifest), encoding="utf-8")
    (kdir / "FILE_HASHES.json").write_text(json.dumps(hashes), encoding="utf-8")
    (kdir / "SYMBOL_INDEX.json").write_text(json.dumps(symbols), encoding="utf-8")
    (kdir / "API_MAP.json").write_text(json.dumps(apis), encoding="utf-8")
    (kdir / "DATABASE_MAP.json").write_text(json.dumps(dbs), encoding="utf-8")
    (kdir / "MASTER_KNOWLEDGE.json").write_text(json.dumps(master), encoding="utf-8")

    # Update knowledge hashes to match actual files
    for kf in ["FILE_MANIFEST.json", "FILE_HASHES.json", "SYMBOL_INDEX.json", "API_MAP.json", "DATABASE_MAP.json", "MASTER_KNOWLEDGE.json"]:
        hashes[f"_forensic/knowledge/{kf}"] = get_h(kdir / kf)
    (kdir / "FILE_HASHES.json").write_text(json.dumps(hashes), encoding="utf-8")

    # Mutate synthetic state:
    # 1. Modify file_b.py
    (ws / "file_b.py").write_text("print('B modified')", encoding="utf-8")
    # 2. Delete file_to_delete.py
    (ws / "file_to_delete.py").unlink()
    # 3. Add new_file.py
    (ws / "new_file.py").write_text("print('Brand new')", encoding="utf-8")

    det = ForensicDriftDetector(root_dir=ws, knowledge_dir=kdir, drift_dir=ws / "_forensic" / "drift")
    res = det.detect_drift(write_artifacts=True)

    assert res.verdict == DriftVerdict.DRIFT_DETECTED
    assert res.reconciliation["all_reconciliations_passed"] is True
    assert res.file_changes_summary["modified"] >= 1   # file_b
    assert res.file_changes_summary["missing"] == 1    # file_to_delete
    assert res.file_changes_summary["new"] == 1        # new_file
    assert len(res.artifacts_written) == 7

def test_detector_adversarial_toctou_concurrent_mutation(tmp_path):
    """
    Validates that concurrent filesystem mutations (create/delete/modify race)
    during detect_drift() SHA-256 calculation phase do NOT cause reconciliation failure.
    """
    import hashlib
    import threading
    import time

    ws = tmp_path / "toctou_ws"
    kdir = ws / "_forensic" / "knowledge"
    kdir.mkdir(parents=True)

    manifest = {}
    hashes = {}
    for i in range(100):
        fname = f"file_{i:03d}.txt"
        fp = ws / fname
        fp.write_text(f"content {i}", encoding="utf-8")
        h = hashlib.sha256(fp.read_bytes()).hexdigest()
        hashes[fname] = h
        manifest[fname] = {"path": fname, "size_bytes": 10, "is_excluded": False}

    for kf in ["FILE_MANIFEST.json", "FILE_HASHES.json", "SYMBOL_INDEX.json", "API_MAP.json", "DATABASE_MAP.json", "MASTER_KNOWLEDGE.json"]:
        manifest[f"_forensic/knowledge/{kf}"] = {"path": f"_forensic/knowledge/{kf}", "size_bytes": 100, "is_excluded": True}
        hashes[f"_forensic/knowledge/{kf}"] = "000"

    (kdir / "FILE_MANIFEST.json").write_text(json.dumps(manifest), encoding="utf-8")
    (kdir / "FILE_HASHES.json").write_text(json.dumps(hashes), encoding="utf-8")
    (kdir / "SYMBOL_INDEX.json").write_text(json.dumps({"classes": {}, "functions": {}}), encoding="utf-8")
    (kdir / "API_MAP.json").write_text(json.dumps({"http_routes": [], "websocket_routes": []}), encoding="utf-8")
    (kdir / "DATABASE_MAP.json").write_text(json.dumps({"databases": {}}), encoding="utf-8")
    (kdir / "MASTER_KNOWLEDGE.json").write_text(json.dumps({"metrics": {"physical_files_count": len(hashes)}}), encoding="utf-8")

    for kf in ["FILE_MANIFEST.json", "FILE_HASHES.json", "SYMBOL_INDEX.json", "API_MAP.json", "DATABASE_MAP.json", "MASTER_KNOWLEDGE.json"]:
        hashes[f"_forensic/knowledge/{kf}"] = hashlib.sha256((kdir / kf).read_bytes()).hexdigest()
    (kdir / "FILE_HASHES.json").write_text(json.dumps(hashes), encoding="utf-8")

    stop_mutator = threading.Event()
    def mutator():
        c = 0
        while not stop_mutator.is_set():
            c += 1
            f = ws / f"runtime/test_tmp/temp_{c}.tmp"
            f.parent.mkdir(parents=True, exist_ok=True)
            try:
                f.write_text(f"data {c}", encoding="utf-8")
                time.sleep(0.001)
                if f.exists():
                    f.unlink()
            except Exception:
                pass

    t = threading.Thread(target=mutator, daemon=True)
    t.start()

    detector = ForensicDriftDetector(root_dir=ws, knowledge_dir=kdir, drift_dir=ws / "_forensic" / "drift")
    res = detector.detect_drift(write_artifacts=False)

    stop_mutator.set()
    t.join(timeout=1.0)

    assert res.reconciliation["all_reconciliations_passed"] is True
    assert res.reconciliation["equation_1_map_files"]["passed"] is True
    assert res.reconciliation["equation_2_physical_files"]["passed"] is True
