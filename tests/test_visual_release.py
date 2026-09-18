"""
E-ZZIO V9.3 Visual Release Verification Suite
Ensures 100% offline self-containment, UI components, static assets, and visual proof existence.
"""
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from web_server import app

client = TestClient(app)

ROOT_DIR = Path(__file__).resolve().parent.parent
WEB_DIR = ROOT_DIR / "runtime" / "web"
VISUAL_FINAL_DIR = ROOT_DIR / "state" / "audit" / "visual" / "v9.3" / "final"


def test_offline_self_containment_no_cdn():
    """Verify that index.html does NOT reference any external CDN (like cdn.tailwindcss.com)."""
    index_path = WEB_DIR / "index.html"
    assert index_path.exists(), "index.html must exist"
    content = index_path.read_text(encoding="utf-8")

    assert "cdn.tailwindcss.com" not in content, "index.html must NOT contain external Tailwind CDN"
    assert "https://" not in content or "fonts.googleapis.com" not in content, "No external remote scripts/styles"


def test_tactical_css_exists_and_served():
    """Verify ezzio-tactical.css is locally stored and served via static route."""
    css_path = WEB_DIR / "ezzio-tactical.css"
    assert css_path.exists(), "ezzio-tactical.css must exist locally"
    assert css_path.stat().st_size > 1000, "ezzio-tactical.css must be populated"

    response = client.get("/static/ezzio-tactical.css")
    assert response.status_code == 200
    assert "text/css" in response.headers.get("content-type", "")


def test_manifest_served():
    """Verify web manifest is served for PWA / Android installation."""
    response = client.get("/static/manifest.json")
    assert response.status_code == 200
    data = response.json()
    assert "Sovereign AI Office" in data.get("name", "")
    assert data.get("display") == "standalone"


def test_critical_ui_dom_anchors():
    """Verify critical tactical DOM elements are present in index.html."""
    index_path = WEB_DIR / "index.html"
    content = index_path.read_text(encoding="utf-8")

    anchors = [
        'id="badge-ledger"',
        'id="provider-badges-group"',
        'id="agent-drawer"',
        'id="hitl-modal"',
        'id="hitl-banner"',
        'id="rooms-grid"',
        'id="btn-mode-observer"',
        'id="btn-mode-commander"',
    ]
    for anchor in anchors:
        assert anchor in content, f"Missing required UI DOM element: {anchor}"


def test_visual_proof_artifacts_exist_and_valid():
    """Verify all 8 certified visual screenshots exist, are valid non-empty PNGs (>20KB)."""
    expected_screenshots = [
        "01-command-center.png",
        "02-office-overview.png",
        "03-agent-inspector.png",
        "04-task-view.png",
        "05-hitl-view.png",
        "06-provider-view.png",
        "07-mobile-portrait.png",
        "08-mobile-landscape.png",
    ]

    assert VISUAL_FINAL_DIR.exists(), f"Visual directory {VISUAL_FINAL_DIR} must exist"

    for filename in expected_screenshots:
        file_path = VISUAL_FINAL_DIR / filename
        assert file_path.exists(), f"Missing visual capture proof: {filename}"
        size = file_path.stat().st_size
        assert size > 20000, f"Screenshot {filename} seems truncated or empty ({size} bytes)"

        # Check PNG header signature
        with open(file_path, "rb") as f:
            header = f.read(8)
            assert header == b"\x89PNG\r\n\x1a\n", f"{filename} is not a valid PNG binary"
