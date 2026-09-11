# E-ZZIO V9.0 — RELEASE NOTES & VERIFICATION MATRIX

## 1. Product Summary
- **Version**: `9.0.0`
- **Codename**: *Sovereign Living AI Office & Multi-Client Suite*
- **Target Distribution**:
  - **Desktop Windows**: Standalone windowed launcher with multi-Chromium `--app` detection (Brave, Edge, Chrome).
  - **Android APK**: Package `dist/android/E-ZzIO-v9.0.0.apk` containing responsive mobile PWA client and zero secrets.
  - **Web Local / Remote**: PWA with Service Worker offline caching, living procedural SVG avatars, 8 rooms, 10 agents, live thought bubbles, code activity, and real-time HITL governance.

---

## 2. Release Verification Matrix

| Component | Target Contract | Verified Status | Evidence |
| :--- | :--- | :--- | :--- |
| **Frozen Core** | 3 Sovereign Pillars SHA-256 sealed | **PASS** | SHA-256 match `docs/FROZEN_CORE_MANIFEST.json` |
| **Living AI Office** | 8 rooms, 10 agents, procedural SVGs, real logs | **PASS** | 15/15 tests in `test_ai_office_visual.py` |
| **HITL Core & API** | REQUIRE_HUMAN, decide, TTL, zero-secrets | **PASS** | 30/30 tests in `test_hitl_api`, `cli`, `discord` |
| **Hermes MCP Bridge** | Confinement, read-only tools, HITL gate | **PASS** | 5/5 tests in `test_hermes_mcp_confinement.py` |
| **Desktop Launcher** | Multi-Chromium `--app` standalone launcher | **PASS** | `tools/launch_desktop.ps1` |
| **Android APK** | Reproducible, clean container without credentials | **PASS** | `dist/android/E-ZzIO-v9.0.0.apk` |
| **Offline Mode** | System font fallbacks, Service Worker cache | **PASS** | `tests/test_product_lifecycle.py` |
| **Regression Suite** | 97/97 tests pass with 0 errors | **PASS** | Full pytest regression gate (100% SUCCESS) |

---

## 3. Provenance & Dependency Compliance
- **Assets**: Verified under `assets/ASSET_LICENSES.json` (Apache-2.0 / SIL OFL 1.1).
- **Dependencies**: Verified under `docs/DEPENDENCIES.md` (Strict PyPI & standard library reusability).
- **Antigravity Status**: Reported as `BLOCKED_BY_EXTERNAL_QUOTA` (Non-blocking external fail-safe).
