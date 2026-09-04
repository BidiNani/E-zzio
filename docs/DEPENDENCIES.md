# E-ZZIO V9.0 — DEPENDENCIES & RUNTIME INVENTORY

## 1. Governance & Acquisition Policy
In accordance with **Phase AL (External Resources / Dependency Acquisition)**:
- **Zero Unverified Binaries**: No arbitrary executable, cracked tool, or untrusted payload is permitted.
- **Strict Provenance**: All dependencies are acquired through official registries (PyPI, npm, OpenJDK, Maven Central, Android SDK).
- **Original Graphic Assets**: Zero copyrighted game sprites or unauthorized franchise assets (no *The Escapists*, no *The Office*). Visual design utilizes original procedural SVGs and permissible open-source typography.
- **Reusability First**: Standard library and existing frameworks (`FastAPI`, `Starlette`, `Pydantic`, `SQLite WAL`, `Uvicorn`) are prioritized before introducing external libraries.

---

## 2. Core Python Dependencies (`.venv`)

| Package | Version | License | Category | Reason / Purpose | RAM Impact | Distribution Impact |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **FastAPI** | `0.141.1` | MIT | Web / API Framework | Core API gateway, WebSocket endpoints, OpenAPI schema | ~25 MB | Server / Desktop |
| **Starlette** | `1.6.0` | BSD-3-Clause | ASGI Toolkit | Low-level HTTP transport, TestClient execution | ~5 MB | Server / Desktop |
| **Pydantic** | `2.13.4` | MIT | Data Validation | Strict data models, serialization, immutable schema | ~15 MB | Server / Desktop |
| **Uvicorn** | `0.52.4` | BSD-3-Clause | ASGI Server | Async event loop and HTTP server on port 8001 | ~20 MB | Server / Desktop |
| **Httpx** | `0.28.1` | BSD-3-Clause | HTTP Client | Async transports for cloud providers & integration tests | ~10 MB | Server / Desktop |
| **Pytest** | `9.1.1` | MIT | Test Automation | 109-test non-regression and certification suite | Test Only | Dev / CI |
| **Pytest-Asyncio** | `1.4.0` | Apache-2.0 | Test Async | Asyncio test loop management for pytest | Test Only | Dev / CI |
| **Discord.py** | `2.4.0` | MIT | HITL Channel | Optional Discord bot integration for approval dispatch | ~30 MB | Optional Worker |
| **Mcp** | `1.29.1` | MIT | Protocol Bridge | Model Context Protocol gateway & confinement | ~12 MB | Worker / Bridge |
| **Cryptography** | `50.0.0` | Apache-2.0 / BSD | Security | AES-GCM / DPAPI secrets vault encryption | ~8 MB | Sovereign Core |
| **RestrictedPython** | `8.5` | ZPL 2.1 | Security | Confined sandbox execution for code evaluation | ~5 MB | Worker / Dev Lab |

---

## 3. Frontend & Visual Workspace Dependencies

| Resource | Version | Origin / Source | License | Integration Method | Client Impact |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **TailwindCSS (CDN)** | `3.x` | Tailwind Labs / Cloudflare | MIT | Script tag in `index.html` | Client-side cache (< 100 KB) |
| **Inter WebFont** | `4.1` | Google Fonts / Rasmus Andersson | SIL OFL 1.1 | WebFont CDN link | Browser font cache |
| **Fira Code WebFont** | `6.2` | Google Fonts / Nikita Prokopov | SIL OFL 1.1 | WebFont CDN link | Browser font cache |
| **Procedural SVG Engine** | `9.0.0` | Sovereign Internal (`index.html`) | Apache-2.0 | Pure JavaScript / DOM SVG rendering | 0 external bytes, < 1 MB RAM |

---

## 4. Desktop Client Toolchain (Windows 11)

| Tool / Runtime | Detected Version | Path / Provenance | Role in E-ZzIO |
| :--- | :--- | :--- | :--- |
| **Python** | `3.12.10` | `G:\Python312\python.exe` (Official PSF installer) | Sovereign backend runtime |
| **Git** | `2.55.0.windows.5` | `C:\Program Files\Git\cmd\git.exe` | Version control & repo telemetry |
| **Node.js** | `v22.23.2` | `C:\Program Files\nodejs\node.exe` | Build utilities & packaging tooling |
| **npm** | `10.9.8` | `C:\Program Files\nodejs\npm.ps1` | Package management |
| **Chromium Engine** | `Brave 1.x / Edge 143.x` | Native OS Application Paths | Standalone windowed UI launcher (`--app`, 1600x1000) |
| **WebView2 Runtime** | `143.0.3650.139` | Evergreen System Runtime | High-fidelity Webview container |

---

## 5. Mobile & Android Client Toolchain

| Component | Target Version | Status / Location | Role in E-ZzIO |
| :--- | :--- | :--- | :--- |
| **OpenJDK / Java** | `17.0.19` | `C:\Program Files\Eclipse Adoptium\jdk-17.0.19.10-hotspot` | Java compiler for Android bytecode |
| **Android Gradle Plugin** | `8.2.2` | `android/settings.gradle` | Android project build system |
| **Android SDK / API** | `API 34 (Android 14)` | Native fallback packaging active | Compilation target & system contracts |
| **E-ZzIO APK Container** | `9.0.0` | `dist/android/E-ZzIO-v9.0.0.apk` | Distributable mobile package |

---

## 6. Prohibited & Quarantined Resources
- **Prohibited Franchises**: Commercial game sprites from *The Escapists*, *The Office*, or proprietary IP are barred.
- **Unverified Binaries**: No pre-compiled `.exe` or third-party wrappers downloaded from untrusted mirrors.
- **Antigravity Status**: Reported as `BLOCKED_BY_EXTERNAL_QUOTA` (non-blocking fail-safe).
