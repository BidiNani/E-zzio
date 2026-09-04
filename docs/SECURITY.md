# E-ZZIO V9.0 — PRODUCT SECURITY ARCHITECTURE

## 1. Sovereignty Principles
- **Backend-Authoritative Governance**: The UI (Desktop, Web PWA, Android APK) is strictly an inspection and controlled dispatch view. Zero sovereign policy logic or security gating is hosted in the client.
- **Frozen Core Immobility**: The 3 sovereign pillars (`core/capabilities/capability_policy.py`, `core/capabilities/registry.py`, `core/security/audit_ledger.py`) are strictly sealed (SHA-256 scellé).
- **Mandatory HITL Interception**: Any mutative, dangerous or external action (`drive.write`, `github.push`, `gmail.send`) triggers `REQUIRE_HUMAN` and halts execution until explicit operator decision.

---

## 2. Secret Scrubbing & Data Sanitation
- **Zero Secrets in Clients**: No API keys (Google `AIza...`, Groq `gsk_...`, Bearer tokens) or credentials are ever stored in the web assets or Android APK bundle.
- **Pending Approvals Sanitation**: The `/api/v1/approvals/pending` endpoint returns only sanitized summaries (`safe_summary`, `scope`, `time_remaining_sec`). Raw payloads with credentials (`params_payload`) remain isolated in server-side storage.
- **Terminal Log Filtering**: Agent terminal outputs only render whitelisted command status (pytest, git, build, ledger status) and strip all bearer tokens and keys.

---

## 3. Sandboxing & Capability Confinement
- **Internal Workers**: Restricted to scoped access definitions in `CapabilityPolicy`.
- **External Subagents (Hermes MCP)**: Confined within the MCP Gateway harness. Read tools are permitted; all mutative requests are intercepted by E-ZZIO HITL.
- **Provider Quota Fail-Safe**: When an external provider encounters quota exhaustion (e.g. Antigravity reported as `BLOCKED_BY_EXTERNAL_QUOTA`), the system degrades gracefully into standby without crashing or blocking local workers.
