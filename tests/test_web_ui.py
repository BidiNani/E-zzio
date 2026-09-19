"""
E-ZZIO V9.4 — Web UI Automated Forensic Test Suite
Validates the served web UI, endpoints, static assets, script integrity,
DOM contracts, security escaping, and bidirectional backend integration.
"""
import json
import re
import urllib.error
import urllib.request
from pathlib import Path

import pytest

BASE_URL = "http://127.0.0.1:8001"
WEB_DIR = Path(r"G:\AI\E-zzio\runtime\web")


def fetch_url(path, method="GET", data=None, headers=None):
    url = f"{BASE_URL}{path}"
    req_headers = headers or {}
    if data and isinstance(data, dict):
        body = json.dumps(data).encode("utf-8")
        req_headers["Content-Type"] = "application/json"
    elif data and isinstance(data, bytes):
        body = data
    else:
        body = None

    try:
        req = urllib.request.Request(url, data=body, headers=req_headers, method=method)
        with urllib.request.urlopen(req, timeout=1.0) as resp:
            content = resp.read()
            return resp.status, dict(resp.headers), content
    except urllib.error.HTTPError:
        raise
    except (urllib.error.URLError, ConnectionRefusedError, TimeoutError, OSError):
        from starlette.testclient import TestClient

        from web_server import app
        with TestClient(app, raise_server_exceptions=False) as client:
            kw = {"headers": req_headers}
            if body:
                kw["content"] = body
            resp = client.request(method, path, **kw)
            if resp.status_code >= 400:
                raise urllib.error.HTTPError(
                    url, resp.status_code, getattr(resp, "reason", "Error"), resp.headers, None
                )
            return resp.status_code, dict(resp.headers), resp.content


# ==============================================================================
# 1. SERVER & ROUTE AVAILABILITY TESTS
# ==============================================================================
def test_backend_health_online():
    status, headers, content = fetch_url("/health")
    assert status == 200
    data = json.loads(content.decode("utf-8"))
    assert data.get("status") == "ONLINE"
    assert data.get("ok") is True


def test_index_served_and_v94():
    status, headers, content = fetch_url("/")
    assert status == 200
    html = content.decode("utf-8")
    assert "<title>E-ZZIO V9.4 — Tactical Sovereign AI Command Center</title>" in html
    assert "V9.4 COMMAND" in html
    assert "FROZEN CORE INTACT" in html


def test_static_assets_served():
    for asset in [
        "/static/ezzio-tactical.css",
        "/static/ezzio-office-motion.js",
        "/static/ezzio-office-canvas.js",
    ]:
        status, headers, content = fetch_url(asset)
        assert status == 200, f"Asset {asset} failed with {status}"
        assert len(content) > 100


def test_service_worker_and_manifest():
    status, headers, content = fetch_url("/static/sw.js")
    assert status == 200
    sw_code = content.decode("utf-8")
    assert "ezzio-office-v9.4.1" in sw_code or "ezzio-office-v9.4" in sw_code

    status_m, _, content_m = fetch_url("/static/manifest.json")
    assert status_m == 200
    manifest = json.loads(content_m.decode("utf-8"))
    assert "E-ZZIO" in manifest.get("name", "")


# ==============================================================================
# 2. SCRIPT DEDUPLICATION & ARCHITECTURE INTEGRITY
# ==============================================================================
def test_script_tags_deduplicated():
    html_path = WEB_DIR / "index.html"
    assert html_path.exists()
    html = html_path.read_text(encoding="utf-8")

    assert '<script src="ezzio-office-motion.js"></script>' not in html
    assert '<script src="ezzio-office-canvas.js"></script>' not in html
    assert html.count('<script src="/static/ezzio-office-motion.js"></script>') == 1
    assert html.count('<script src="/static/ezzio-office-canvas.js"></script>') == 1


def test_canvas_open_drawer_binding():
    html = (WEB_DIR / "index.html").read_text(encoding="utf-8")
    assert "window.openAgentDrawer = inspectAgent;" in html


def test_escape_html_security_utility():
    html = (WEB_DIR / "index.html").read_text(encoding="utf-8")
    assert "function escapeHtml(str)" in html
    assert "replace(/&/g, '&amp;')" in html
    assert "replace(/</g, '&lt;')" in html
    assert "replace(/>/g, '&gt;')" in html


# ==============================================================================
# 3. CANONICAL API ENDPOINT VALIDATION
# ==============================================================================
def test_canonical_office_state_api():
    status, _, content = fetch_url("/master/api/v1/office/state")
    assert status == 200
    state = json.loads(content.decode("utf-8"))
    assert state.get("ok") is True
    assert "summary" in state
    assert state["summary"]["total_agents"] == 10
    assert len(state["rooms"]) >= 8
    assert len(state["agents"]) == 10

    master = next((a for a in state["agents"] if a["agent_id"] == "master_ezzio"), None)
    assert master is not None
    assert master["is_master"] is True
    assert master["room"] == "command_center"


def test_canonical_office_map_api():
    status, _, content = fetch_url("/master/api/v1/office/map")
    assert status == 200
    omap = json.loads(content.decode("utf-8"))
    assert omap.get("ok") is True
    assert omap.get("grid_width") == 36
    assert omap.get("grid_height") == 24
    assert "command_center" in omap.get("rooms", {})
    assert "dev_lab" in omap.get("rooms", {})


def test_canonical_office_events_api():
    status, _, content = fetch_url("/master/api/v1/office/events")
    assert status == 200
    ev = json.loads(content.decode("utf-8"))
    assert ev.get("ok") is True
    assert isinstance(ev.get("events"), list)


def test_canonical_approvals_api():
    status, _, content = fetch_url("/master/api/v1/approvals/pending")
    assert status == 200
    appr = json.loads(content.decode("utf-8"))
    assert appr.get("ok") is True
    assert "pending_approvals" in appr


def test_canonical_providers_health_api():
    status, _, content = fetch_url("/master/api/v1/providers/health")
    assert status == 200
    health = json.loads(content.decode("utf-8"))
    assert health.get("ok") is True
    providers = health.get("health", {}).get("providers", {})
    assert "ollama" in providers
    assert "gemini" in providers


def test_canonical_system_diagnostics_api():
    status, _, content = fetch_url("/master/api/v1/system/diagnostics")
    assert status == 200
    diag = json.loads(content.decode("utf-8"))
    assert diag.get("ok") is True
    assert "audit_ledger" in diag
    assert diag["audit_ledger"]["status"] == "SECURE"


# ==============================================================================
# 4. CHAT INTENT CONTRACT & RESILIENCE
# ==============================================================================
def test_master_chat_schema_contract():
    status, _, content = fetch_url("/master/chat", method="POST", data={"text": "audit status ping"})
    assert status == 200
    res = json.loads(content.decode("utf-8"))
    assert res.get("ok") is True or "response" in res or "message" in res or res.get("status") == "SUCCESS"

    try:
        fetch_url("/master/chat", method="POST", data={"message": "invalid"})
        raise AssertionError("Should have thrown 422 HTTP error")
    except urllib.error.HTTPError as e:
        assert e.code == 422
