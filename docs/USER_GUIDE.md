# 🛡️ E-ZZIO V9.3 — OPERATOR USER GUIDE
## Tactical Sovereign AI Command Center (Desktop & Android)

Welcome to the official **E-ZZIO V9.3 Operator Guide**. E-ZZIO is a sovereign, self-contained, multi-agent cognitive operating system with strict capability-based governance, cryptographic auditability, and cross-platform operator interfaces.

---

## 1. Quick Start (Desktop & Server)

### 1.1 Launching the Sovereign Backend
From PowerShell in `G:\AI\E-zzio`:
```powershell
.\.venv\Scripts\Activate.ps1
python -m uvicorn web_server:app --host 0.0.0.0 --port 8001
```
The server will initialize on port 8001, mounting:
- FastAPI REST & WebSocket APIs (`/master/api/v1/...`)
- Static Tactical UI assets (`/static/...`)
- High-performance NVMe caching and SQLite Audit Ledger

### 1.2 Accessing the Command Center
Open any modern browser (Brave, Chrome, Edge, Firefox) or run:
```powershell
.\tools\launch_desktop.ps1
```
Navigate to:
👉 **`http://127.0.0.1:8001`**

The entire interface operates **100% offline** without any external CDN or remote asset dependencies.

---

## 2. Navigating the Tactical AI Office

### 2.1 The 8-Room Living Floor Plan
The command center visualizes the 8 cognitive zones of the E-ZZIO collective:
1. **Command Center** (`master_ezzio`): Oversees collective goals, orchestrates subagents, and routes natural language intents.
2. **Security Vault** (`security_guardian`): Enforces `CapabilityPolicy` and monitors the cryptographic Audit Ledger.
3. **Code Lab** (`hermes_coder`): Generates code within confined MCP sandboxes.
4. **Research Archive** (`perception_agent`): Manages document ingestion, Chroma vector store embeddings, and RAG retrieval.
5. **DevOps Runway** (`devops_pipeline`): Manages automated testing, builds, and Android APK deployment.
6. **Federation Hub** (`federation_router`): Routes requests between Gemini 3.7 Cloud, Groq Llama, and local Ollama Qwen models.
7. **HITL Sanctuary** (`hitl_arbiter`): Holds intercepted mutating actions pending human approval.
8. **Android Bridge** (`android_bridge`): Synchronizes state with mobile Android nodes via ADB.

### 2.2 Inspecting Agents (Inspector 2.0)
Click the **"Inspect 🔎"** button on any agent card or click an agent avatar in the minimap to slide out the **Agent Inspector**:
- **Real-Time Thought Stream**: See the exact internal chain-of-thought of the agent.
- **Governed Capabilities**: Review which tools (`memory.read`, `system.exec`, `drive.write`) the agent is authorized to execute.
- **Task Progress**: Track execution percentage and active subtask.
- **Terminal Output**: View raw stdout/stderr logs directly from the agent runtime.

### 2.3 Human-in-the-Loop (HITL) Governance
When an agent attempts a sensitive or mutating operation (e.g. `drive.write`, deleting files, running arbitrary shell commands):
1. The action is **halted immediately** with fail-closed security.
2. The top glowing **HITL Interception Banner** will illuminate with an audible/visual alert and countdown timer.
3. Click **"Examiner & Arbitrer"** to open the arbitration modal.
4. Review the payload diff and cryptographic SHA-256 hash.
5. Provide an operator motivation note, then click:
   - **APPROUVER LA MUTATION**: Resumes the action and records human approval in the immutable ledger.
   - **REJETER (Fail-Closed)**: Cancels the action immediately and revokes the capability token.

---

## 3. Android Mobile Tactical Experience

### 3.1 Architecture & Installation
The Android companion application (`ai.ezzio.office`) is a native Android package compiled with Android SDK 34, signed with APK Signature Scheme v2, and verified against classes.dex bytecode.

To install or verify on a connected device or emulator:
```powershell
G:\tools\platform-tools\adb.exe install -r dist\android\E-ZzIO-v9.1-release.apk
```

### 3.2 Launching the Mobile App
Run:
```powershell
G:\tools\platform-tools\adb.exe shell am start -n ai.ezzio.office/.MainActivity
```
The mobile interface connects to the local sovereign server (via `10.0.2.2:8001` on emulator or local LAN IP on physical devices).
It automatically adapts to:
- **Portrait (Vertical)**: Single-column streamlined card stack with touch-friendly controls.
- **Landscape (Horizontal)**: 2-column tactical view with side-by-side telemetry.

---

## 4. Operational Modes & Accessibility

- **Observer Mode (🎥)**: Automatically pans and highlights agents as they perform work, ideal for large monitoring displays.
- **Commander Mode (⚡)**: Interactive mode allowing operators to inject tasks, approve mutations, and halt agents.
- **Reduced Motion (🏃)**: Disables pulse and glowing animations for operators with vestibular sensitivity or low-power hardware.
- **Sync State (🔄)**: Forces an instant poll of the FastAPI backend state.
