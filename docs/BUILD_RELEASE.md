# E-ZZIO V9.0 — BUILD & RELEASE GUIDE

## 1. Overview
This document details the multi-target packaging and build processes for E-ZzIO V9.0:
- **Desktop Windows** (WebView2 / Standalone App)
- **Web Local & Remote** (PWA / Service Worker)
- **Android APK** (Gradle-compliant offline Android application)

---

## 2. Desktop Windows Launcher
- **Path**: `tools/launch_desktop.ps1`
- **Mechanism**:
  1. Verifies Python venv at `.\.venv\Scripts\python.exe`.
  2. Ensures server is active at `http://127.0.0.1:8001/master/office`.
  3. Launches Microsoft Edge / WebView2 in app mode:
     ```powershell
     msedge.exe --app="http://127.0.0.1:8001/master/office" --window-size=1600,1000
     ```
- **Execution**:
  ```powershell
  pwsh -File tools/launch_desktop.ps1
  ```

---

## 3. Web & PWA Deployment
- **Assets**: `runtime/web/manifest.json`, `runtime/web/sw.js`, `runtime/web/index.html`.
- **Mount Points**:
  - `/master/office` (Primary living visual UI)
  - `/manifest.json` and `/master/manifest.json` (PWA Manifest)
  - `/sw.js` and `/master/sw.js` (Service Worker cache engine)
- **Offline Resilience**:
  - Static caching handles UI rendering even during temporary backend disconnections.
  - Automatic reconnection polling on WebSocket/SSE streams.

---

## 4. Android APK Compilation
- **Script**: `tools/build_android_apk.ps1`
- **Output Target**: `dist/android/E-ZzIO-v9.0.0.apk`
- **Security Check**: Pre-build regex scan automatically scans all assets for API keys (Google, Groq, Bearer tokens). If found, build aborts immediately.
- **Packaging Steps**:
  1. Checks for Android SDK or runs fallback deterministic ZIP-container packaging.
  2. Embeds all PWA assets into `assets/web/`.
  3. Packages compiled Android manifest and bytecode.
  4. Generates signed/aligned artifact in `dist/android/`.
- **Execution**:
  ```powershell
  pwsh -File tools/build_android_apk.ps1
  ```

---

## 5. Certification & Non-Regression Gate
Before releasing any build or commit:
```powershell
.\.venv\Scripts\python.exe -m pytest tests/test_product_certification.py -v
.\.venv\Scripts\python.exe -m pytest tests/test_ai_office_visual.py -v
.\.venv\Scripts\python.exe -m pytest tests/test_ai_office.py -v
```
All 109 tests must pass with 0 errors and 0 warnings.
