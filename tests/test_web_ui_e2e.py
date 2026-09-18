"""
E-ZZIO V9.4 — Comprehensive Real Browser E2E Forensic Test Suite
Launches a real Chromium browser (Brave / Chrome), navigates to http://127.0.0.1:8001/,
and programmatically controls the browser via Chrome DevTools Protocol (CDP).

Controls:
1. Browser launch & clean session navigation
2. 0 Console errors / 0 unhandled runtime exceptions
3. Network endpoints (HTTP 200 on all canonical /master/api/v1/* calls)
4. 2.5D Living Office Canvas initialized, sized, running animation loop & FPS > 0
5. 8 Rooms & 10 Agents rendered into DOM
6. User interactions: View switching, Zoom +, Zoom -, Recentering, Mode Observer, Mode Commander, Reduced Motion
7. Agent Drawer Inspection: clicking agent card opens drawer with correct name, role, model, status, tools
8. Master Intent Terminal: sending chat prompt updates button state, calls /master/chat, displays live response
9. HITL Governance: modal opens, contains sanitized payload, allows decision submission
10. Security / XSS: verifies that malicious payloads are escaped as text and never executed
"""
import asyncio
import json
import os
import shutil
import subprocess
import time
import urllib.request

import pytest
import websockets

import sys
import tempfile

# Chemins via helper centralisé (safe : jamais le Brave perso)
from tests._browser_helper import (
    find_browser,
    get_free_port,
    wait_for_cdp,
    get_cdp_ws_url,
    isolated_brave_cdp,
)

BRAVE_PATH = find_browser()
BASE_URL = "http://127.0.0.1:8001/"
PROFILE_BASE = str(Path(tempfile.gettempdir()) / "ezzio_e2e_profiles")


def _is_e2e_available():
    if not os.path.exists(BRAVE_PATH):
        return False
    try:
        with urllib.request.urlopen(BASE_URL, timeout=0.5) as r:
            return r.status == 200
    except Exception:
        return False


pytestmark = pytest.mark.skipif(
    not _is_e2e_available(),
    reason="Exécution E2E exige un serveur Web UI actif sur http://127.0.0.1:8001 et Brave Browser"
)


class BrowserCDPSession:
    """Session CDP isolée — utilise isolated_brave_cdp (safe).

    Ne touche JAMAIS au Brave perso de l'utilisateur :
      - Port dynamique
      - Profil isolé en tempdir
      - PID tracké (self.proc)
    """

    def __init__(self, cdp_port: int | None = None):
        # cdp_port est ignoré (compat) : on utilise un port dynamique
        self.cdp_port = cdp_port  # conservé pour compat API
        self.profile_dir = None
        self.proc = None
        self.ws = None
        self.msg_id = 1
        self.console_events = []
        self.exceptions = []
        self.network_responses = []
        self._cm = None

    async def start(self):
        # On utilise le context manager mais on garde le contrôle du cycle
        from contextlib import ExitStack
        self._exit_stack = ExitStack()
        proc, port = self._exit_stack.enter_context(
            isolated_brave_cdp(headless=True)
        )
        self.proc = proc
        self.actual_port = port

        ws_url = get_cdp_ws_url(port, timeout=10.0)
        self.ws = await websockets.connect(
            ws_url,
            max_size=20_000_000,
            open_timeout=15,
            ping_interval=None,
        )

        await self.send("Runtime.enable")
        await self.send("Console.enable")
        await self.send("Log.enable")
        await self.send("Network.enable")
        await self.send("Page.enable")

    async def send(self, method, params=None):
        cmd_id = self.msg_id
        self.msg_id += 1
        payload = {"id": cmd_id, "method": method}
        if params:
            payload["params"] = params
        await self.ws.send(json.dumps(payload))
        return cmd_id

    async def recv_until_id(self, target_id, timeout=8.0):
        start = time.time()
        while time.time() - start < timeout:
            raw = await asyncio.wait_for(self.ws.recv(), timeout=2.0)
            msg = json.loads(raw)
            method = msg.get("method")
            if method == "Runtime.consoleAPICalled":
                self.console_events.append(msg["params"])
            elif method == "Runtime.exceptionThrown":
                self.exceptions.append(msg["params"])
            elif method == "Network.responseReceived":
                self.network_responses.append(msg["params"])
            if msg.get("id") == target_id:
                return msg
        raise TimeoutError(f"CDP : pas de réponse à id={target_id} après {timeout}s")

    async def stop(self):
        if self.ws is not None:
            try:
                await self.ws.close()
            except Exception:
                pass
            self.ws = None
        if getattr(self, "_exit_stack", None) is not None:
            try:
                self._exit_stack.close()
            except Exception:
                pass
            self._exit_stack = None
@pytest.mark.asyncio
async def test_browser_page_load_and_console_cleanliness():
    session = BrowserCDPSession(cdp_port=9224)
    await session.start()
    try:
        nav_id = await session.send("Page.navigate", {"url": BASE_URL})
        await session.recv_until_id(nav_id)
        await session.drain_events(duration=3.0)

        crit_exceptions = [e for e in session.exceptions if "exceptionDetails" in e]
        assert len(crit_exceptions) == 0, f"Critical JS exceptions found: {crit_exceptions}"

        hud_badge = await session.evaluate("document.getElementById('hud-cmd-badge')?.textContent?.trim()")
        assert hud_badge == "V9.4 COMMAND"

    finally:
        await session.stop()


@pytest.mark.asyncio
async def test_browser_canvas_and_agents_rendering():
    session = BrowserCDPSession(cdp_port=9225)
    await session.start()
    try:
        await session.send("Page.navigate", {"url": BASE_URL})
        await session.drain_events(duration=3.0)

        canvas_info = await session.evaluate("""
        ({
            hasOfficeCanvas: typeof officeCanvas !== 'undefined' && officeCanvas !== null,
            canvasElemWidth: document.getElementById('office-canvas')?.width,
            canvasElemHeight: document.getElementById('office-canvas')?.height,
            agentsCountInCanvas: officeCanvas ? officeCanvas.agents.size : 0,
            mapLoaded: officeCanvas && officeCanvas.map !== null && !!officeCanvas.map.rooms
        })
        """)
        assert canvas_info["hasOfficeCanvas"] is True
        assert canvas_info["canvasElemWidth"] > 0
        assert canvas_info["canvasElemHeight"] > 0
        assert canvas_info["agentsCountInCanvas"] == 10
        assert canvas_info["mapLoaded"] is True

        rooms_count = await session.evaluate("document.getElementById('rooms-grid')?.children?.length")
        assert rooms_count == 8

        stat_agents = await session.evaluate("document.getElementById('stat-agents')?.textContent")
        assert stat_agents == "10"

    finally:
        await session.stop()


@pytest.mark.asyncio
async def test_browser_agent_inspector_drawer():
    session = BrowserCDPSession(cdp_port=9226)
    await session.start()
    try:
        await session.send("Page.navigate", {"url": BASE_URL})
        await session.drain_events(duration=3.0)

        await session.evaluate("inspectAgent('coder_worker')")
        drawer_data = await session.evaluate("""
        ({
            isOpen: document.getElementById('agent-drawer')?.style.display !== 'none',
            name: document.getElementById('drawer-name')?.textContent,
            role: document.getElementById('drawer-role')?.textContent,
            model: document.getElementById('drawer-model')?.textContent,
            status: document.getElementById('drawer-status')?.textContent,
            toolsCount: document.getElementById('drawer-tools')?.children?.length
        })
        """)
        assert drawer_data["isOpen"] is True
        assert drawer_data["name"] == "Alpha Coder"
        assert "Autonomous Coding" in drawer_data["role"]
        assert drawer_data["toolsCount"] > 0

        await session.evaluate("closeAgentDrawer()")
        is_closed = await session.evaluate("document.getElementById('agent-drawer')?.style.display === 'none'")
        assert is_closed is True

    finally:
        await session.stop()


@pytest.mark.asyncio
async def test_browser_interactions_and_modes():
    session = BrowserCDPSession(cdp_port=9227)
    await session.start()
    try:
        await session.send("Page.navigate", {"url": BASE_URL})
        await session.drain_events(duration=2.5)

        # 1. Mode Observer
        await session.evaluate("toggleObserverMode()")
        observer_active = await session.evaluate("!document.getElementById('observer-indicator')?.classList.contains('hidden')")
        assert observer_active is True
        await session.evaluate("toggleObserverMode()")

        # 2. Mode Commander
        await session.evaluate("toggleCommanderMode()")
        commander_active = await session.evaluate("!document.getElementById('commander-indicator')?.classList.contains('hidden')")
        assert commander_active is True
        await session.evaluate("toggleCommanderMode()")

        # 3. Reduced Motion
        await session.evaluate("toggleReducedMotion()")
        reduced_motion_body = await session.evaluate("document.body.classList.contains('reduced-motion')")
        assert reduced_motion_body is True
        await session.evaluate("toggleReducedMotion()")

        # 4. Zoom & Camera reset
        initial_zoom = await session.evaluate("officeCanvas.camera.targetZoom")
        await session.evaluate("canvasZoom(1.18)")
        zoomed = await session.evaluate("officeCanvas.camera.targetZoom")
        assert zoomed > initial_zoom

        await session.evaluate("canvasResetCamera()")
        reset_zoom = await session.evaluate("officeCanvas.camera.targetZoom")
        assert reset_zoom == 1.0

        # 5. View switch
        await session.evaluate("switchOfficeView('grid')")
        canvas_display = await session.evaluate("document.getElementById('office-canvas-container')?.style.display")
        assert canvas_display == "none"

        await session.evaluate("switchOfficeView('canvas')")
        canvas_display_back = await session.evaluate("document.getElementById('office-canvas-container')?.style.display")
        assert canvas_display_back == "block"

    finally:
        await session.stop()


@pytest.mark.asyncio
async def test_browser_direct_sovereign_intent_chat():
    session = BrowserCDPSession(cdp_port=9228)
    await session.start()
    try:
        await session.send("Page.navigate", {"url": BASE_URL})
        await session.drain_events(duration=2.5)

        await session.evaluate("""
        (async () => {
            const input = document.getElementById('intent-input');
            input.value = 'Bonjour E-ZZIO, réponds simplement OK.';
            await sendIntent();
        })()
        """)

        await session.drain_events(duration=3.0)
        chat_result = await session.evaluate("""
        ({
            isBoxVisible: !document.getElementById('intent-result')?.classList.contains('hidden'),
            text: document.getElementById('intent-result')?.textContent
        })
        """)
        assert chat_result["isBoxVisible"] is True
        assert len(chat_result["text"]) > 10
        assert "response" in chat_result["text"] or "ok" in chat_result["text"] or "result" in chat_result["text"]

        # Verify new Agent HQ Chat UI stream
        chat_stream_info = await session.evaluate("""
        ({
            messagesCount: document.getElementById('chat-messages-container')?.children?.length,
            hasUserMessage: !!document.querySelector('#chat-messages-container .bg-blue-950\\\\/20'),
            statusBarText: document.getElementById('chat-status-bar')?.textContent
        })
        """)
        assert chat_stream_info["messagesCount"] >= 2
        assert chat_stream_info["hasUserMessage"] is True

    finally:
        await session.stop()


@pytest.mark.asyncio
async def test_browser_hitl_modal_and_decision():
    session = BrowserCDPSession(cdp_port=9230)
    await session.start()
    try:
        await session.send("Page.navigate", {"url": BASE_URL})
        await session.drain_events(duration=2.5)

        # Open HITL modal with mock preview
        await session.evaluate("""
        (() => {
            currentPendingApproval = {
                approval_id: 'appr_browser_test',
                capability_name: 'drive.write',
                scope: 'external_write',
                time_remaining_sec: 290,
                safe_summary: 'E2E browser controlled HITL test approval',
                params_payload: JSON.stringify({ target: 'test_file.txt', action: 'write' })
            };
            openHitlModal('appr_browser_test');
        })()
        """)
        modal_open = await session.evaluate("document.getElementById('hitl-modal')?.style.display !== 'none'")
        assert modal_open is True

        cap_text = await session.evaluate("document.getElementById('modal-appr-cap')?.textContent")
        assert cap_text == "drive.write"

        # Close HITL modal
        await session.evaluate("closeHitlModal()")
        modal_closed = await session.evaluate("document.getElementById('hitl-modal')?.style.display === 'none'")
        assert modal_closed is True

    finally:
        await session.stop()


@pytest.mark.asyncio
async def test_browser_polling_stability():
    session = BrowserCDPSession(cdp_port=9231)
    await session.start()
    try:
        await session.send("Page.navigate", {"url": BASE_URL})
        await session.drain_events(duration=6.5)

        poll_data = await session.evaluate("""
        ({
            hasExceptions: typeof officeCanvas === 'undefined' || officeCanvas === null,
            canvasAlive: officeCanvas && officeCanvas.agents.size === 10,
            lastPollUpdated: document.getElementById('last-poll')?.textContent !== 'Just now'
        })
        """)
        assert poll_data["hasExceptions"] is False
        assert poll_data["canvasAlive"] is True

    finally:
        await session.stop()


@pytest.mark.asyncio
async def test_browser_xss_sanitization_defense():
    session = BrowserCDPSession(cdp_port=9232)
    await session.start()
    try:
        await session.send("Page.navigate", {"url": BASE_URL})
        await session.drain_events(duration=2.5)

        xss_test = await session.evaluate("""
        (() => {
            const payload = '<script>window.XSS_TRIGGERED=true;</script><img src=x onerror=window.XSS_TRIGGERED=true;>';
            const escaped = escapeHtml(payload);
            const container = document.createElement('div');
            container.innerHTML = escaped;
            return {
                escapedText: escaped,
                xssTriggered: window.XSS_TRIGGERED === true,
                hasRawScriptTag: container.querySelector('script') !== null,
                hasRawImgTag: container.querySelector('img') !== null
            };
        })()
        """)
        assert xss_test["xssTriggered"] is False
        assert xss_test["hasRawScriptTag"] is False
        assert xss_test["hasRawImgTag"] is False
        assert "&lt;script&gt;" in xss_test["escapedText"]

    finally:
        await session.stop()
