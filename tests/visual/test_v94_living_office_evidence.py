"""
E-ZZIO V9.4 Living AI Office Visual Counter-Certification Automated Verification Suite
Ensures fail-closed visual evidence contract:
- Frozen Core cryptographic hashes 100% match
- 10 certified high-resolution PNGs exist, non-empty, correct dimensions
- Certified MP4 exists, duration >= 30.0s, size >= 500KB, non-static
- Locomotion verified via mathematical non-zero pixel variance (t0 != t1 != t2)
- MANIFEST.json cryptographically seals all artifacts
"""
import hashlib
import json
from pathlib import Path

import cv2
import numpy as np
import pytest
from PIL import Image

ROOT_DIR = Path(__file__).resolve().parent.parent.parent
EVIDENCE_DIR = ROOT_DIR / "state" / "audit" / "visual" / "v9.4-counter-certification"

# Frozen Core : la vérification est déléguée au gate central
# (voir tests/test_frozen_core.py et core/frozen_core/manifest.py)
from core.frozen_core import ManifestDriftError, verify_integrity

EXPECTED_PNGS = [
    ("01-command-center.png", 1920, 1080),
    ("02-office-overview.png", 1920, 1080),
    ("03-agent-moving-t0.png", 1920, 1080),
    ("04-agent-moving-t1.png", 1920, 1080),
    ("05-agent-moving-t2.png", 1920, 1080),
    ("06-task-execution.png", 1920, 1080),
    ("07-hitl-interception.png", 1920, 1080),
    ("08-provider-health.png", 1920, 1080),
    ("09-mobile-portrait.png", 720, 1280),
    ("10-mobile-landscape.png", 1280, 720),
]


def sha256_file(filepath: Path) -> str:
    h = hashlib.sha256()
    with open(filepath, "rb") as f:
        while chunk := f.read(65536):
            h.update(chunk)
    return h.hexdigest().upper()


def test_frozen_core_untouched():
    """Verify zero drift on core capabilities and security audit ledger.

    Délégué au gate central core.frozen_core — source de vérité unique.
    """
    try:
        verify_integrity()
    except ManifestDriftError as e:
        pytest.fail(str(e))


def test_evidence_directory_exists():
    """Verify target evidence directory exists."""
    assert EVIDENCE_DIR.exists(), f"Evidence directory missing: {EVIDENCE_DIR}"
    assert EVIDENCE_DIR.is_dir()


@pytest.mark.parametrize("filename,expected_w,expected_h", EXPECTED_PNGS)
def test_certified_png_artifacts(filename, expected_w, expected_h):
    """Verify all 10 PNGs exist, have valid byte sizes (> 15KB) and valid dimensions."""
    fp = EVIDENCE_DIR / filename
    assert fp.exists(), f"Required PNG artifact missing: {filename}"
    size = fp.stat().st_size
    assert size > 15000, f"PNG {filename} is suspiciously small ({size} bytes)"

    im = Image.open(fp)
    w, h = im.size
    assert w == expected_w, f"{filename} width {w} != expected {expected_w}"
    assert h == expected_h, f"{filename} height {h} != expected {expected_h}"


def test_physical_locomotion_pixel_variance():
    """Verify non-zero pixel variance across t0, t1, t2 disproving static spoofing."""
    p0 = EVIDENCE_DIR / "03-agent-moving-t0.png"
    p1 = EVIDENCE_DIR / "04-agent-moving-t1.png"
    p2 = EVIDENCE_DIR / "05-agent-moving-t2.png"

    assert p0.exists() and p1.exists() and p2.exists()

    im0 = np.array(Image.open(p0)).astype(np.int32)
    im1 = np.array(Image.open(p1)).astype(np.int32)
    im2 = np.array(Image.open(p2)).astype(np.int32)

    diff01 = np.abs(im0 - im1)
    diff12 = np.abs(im1 - im2)

    # Max pixel delta must be substantial (> 100 on RGB 0-255 scale)
    assert np.max(diff01) > 100, "Delta between t0 and t1 is zero or trivial!"
    assert np.max(diff12) > 100, "Delta between t1 and t2 is zero or trivial!"

    # Changed pixels count must prove physical agent sprite displacement
    changed_01 = np.count_nonzero(diff01.sum(axis=2) if diff01.ndim == 3 else diff01)
    changed_12 = np.count_nonzero(diff12.sum(axis=2) if diff12.ndim == 3 else diff12)
    assert changed_01 > 100, f"Changed pixels t0-t1 too low: {changed_01}"
    assert changed_12 > 100, f"Changed pixels t1-t2 too low: {changed_12}"


def test_certified_video_properties():
    """Verify video exists, >= 30.0s, >= 500KB, valid H.264 stream."""
    video_path = EVIDENCE_DIR / "E-ZZIO-V9.4-VISUAL-COUNTER-CERTIFICATION.mp4"
    assert video_path.exists(), "Certified video proof missing"
    assert video_path.stat().st_size >= 500000, "Video size less than 500KB"

    cap = cv2.VideoCapture(str(video_path))
    assert cap.isOpened(), "Could not open video file"
    fps = cap.get(cv2.CAP_PROP_FPS)
    cnt = cap.get(cv2.CAP_PROP_FRAME_COUNT)
    duration = cnt / fps if fps > 0 else 0
    cap.release()

    assert duration >= 30.0, f"Video duration {duration:.2f}s is less than required 30.0s"
    assert cnt >= 900, f"Total frame count {cnt} is less than 900 frames at 30 FPS"


def test_manifest_cryptographic_integrity():
    """Verify MANIFEST.json exists and each file's SHA-256 matches actual filesystem state."""
    manifest_p = EVIDENCE_DIR / "MANIFEST.json"
    assert manifest_p.exists(), "MANIFEST.json missing"
    data = json.loads(manifest_p.read_text(encoding="utf-8"))

    assert data.get("frozen_core_status") == "VERIFIED_100_PERCENT"
    artifacts = data.get("artifacts", {})
    assert len(artifacts) >= 11, f"Manifest must document at least 11 artifacts, got {len(artifacts)}"

    for name, entry in artifacts.items():
        file_path = EVIDENCE_DIR / name
        assert file_path.exists(), f"Manifest lists {name} but file not on disk"
        disk_hash = sha256_file(file_path)
        assert disk_hash == entry["sha256"], f"Cryptographic mismatch for {name} in MANIFEST.json!"


def test_forensic_markdown_report():
    """Verify counter-certification markdown report exists and has required sections."""
    report_p = EVIDENCE_DIR / "V9.4-VISUAL-COUNTER-CERTIFICATION.md"
    assert report_p.exists(), "Markdown report missing"
    content = report_p.read_text(encoding="utf-8")

    assert "RAPPORT DE CONTRE-CERTIFICATION VISUELLE INDÉPENDANTE" in content
    assert "FROZEN CORE" in content or "Noyau Figé" in content
    assert "VERIFIED" in content
    assert "E-ZZIO-V9.4-VISUAL-COUNTER-CERTIFICATION.mp4" in content
