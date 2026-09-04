# E-ZZIO V9.0 — AI OFFICE PRODUCT SPECIFICATION

## 1. Vision & Role
The **E-ZzIO AI Office** is not a cosmetic dashboard or decorative gimmick. It is the real-time visual representation of the sovereign multi-agent collective.
- **E-ZzIO remains Master & Sovereign Governor**: The policy engine, HITL gating, model router, and audit ledger are strictly backend-authoritative.
- **Frontend as View**: The UI provides observation, supervision, and command entry points without hosting security or policy logic.

---

## 2. Core Features & Capabilities

### 2.1 8 Canonical Rooms
1. **Command Center**: Master Governor oversight, priority coordination, global system metrics.
2. **Dev Lab**: Code generation, syntax analysis, local patching.
3. **Research Room**: Deep codebase forensics, dependency graphing, web lookups.
4. **Test Lab**: Regression verification, pytest gates, compliance checks.
5. **Security Vault**: Policy evaluation, scope enforcement, immutable audit ledger.
6. **Docs Room**: Architectural documentation, ADR generation, markdown exports.
7. **DevOps Dock**: Build automation, APK compilation, service health monitoring.
8. **Memory Core**: State persistence, SQLite WAL storage, retrieval embeddings.

### 2.2 10 Real Agents
Each agent is rendered with a distinct procedural SVG avatar (palette, accessories, facial features):
- `master_governor`, `backend_agent`, `frontend_agent`, `security_agent`, `qa_engineer`, `research_agent`, `devops_agent`, `docs_writer`, `architect_agent`, `audit_agent`.

### 2.3 Live Interaction Dynamics
- **Thought Bubbles**: Dynamic thought emissions reflecting internal reasoning or current sub-action.
- **Collaborator Links**: SVG connector lines dynamically drawn between collaborating agents with particle pulses.
- **Live Code Activity**: Real-time syntax-colored diffs/snippets reflecting active modifications.
- **Real Terminal Logs**: Streamed ledger and execution logs from `audit_ledger.db`.
- **Observer Mode**: Automatic camera rotation tracking active agents every 4 seconds.
- **Commander Mode**: Full keyboard & command input interface for dispatching tasks and triggering approvals.
- **Reduced Motion**: Accessibility toggle respecting `prefers-reduced-motion` and manual user preference.

### 2.4 Governance & HITL Integration
- **Live Pipeline**: `PLAN -> POLICY -> HITL CHECK -> RUNNING -> VERIFY -> DONE`.
- **Pulsing Alert Banner**: Red badge and high-priority banner whenever an action enters `AWAITING_APPROVAL` / `REQUIRE_HUMAN`.
- **One-Click Decisions**: Approve or reject directly from the modal or notification bar with mandatory rationale.
