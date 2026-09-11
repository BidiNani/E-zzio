# E-ZZIO V9.0 — SOVEREIGN AI OFFICE ARCHITECTURE

## 1. VISION & FONDEMENTS DU SYSTÈME

Le système **E-ZZIO AI Office** n'est ni un jouet visuel ni une décoration cosmétique. Il constitue la **représentation cartographique et opérationnelle en temps réel** de l'ensemble des agents, sous-agents, outils et processus gouvernés par E-ZZIO.

```text
┌────────────────────────────────────────────────────────────────────────┐
│                        👑 E-ZZIO MASTER GOVERNOR                       │
│           (Policy Authority · Model Router · HITL Core · Audit)         │
└───────────────────────────────────┬────────────────────────────────────┘
                                    │
       ┌────────────────────────────┼────────────────────────────┐
       │                            │                            │
┌──────▼─────────────┐   ┌──────────▼─────────┐    ┌─────────────▼─────────┐
│  LOCAL WORKERS     │   │  SUBAGENTS (MCP)   │    │ FEDERATED PROVIDERS   │
│  - Alpha Coder     │   │  - Hermes Agent    │    │ - Gemini 3.7 Flash    │
│  - Scout Research  │   │    (Confinement    │    │ - Groq Llama 3.3      │
│  - Sentinel QA     │   │     Gateway 8001)  │    │ - Ollama Local Qwen   │
│  - Aegis Security  │   │                    │    │ - Antigravity (Quota) │
└────────────────────┘   └────────────────────┘    └───────────────────────┘
                                    │
                                    ▼
       ┌────────────────────────────────────────────────────────┐
       │             E-ZZIO AI OFFICE VISUAL CANVAS             │
       │       FastAPI /master/api/v1/office/state (Port 8001)   │
       │       8 Rooms · Real-time Telemetry · HITL Decider     │
       └────────────────────────────────────────────────────────┘
```

### 1.1 Invariants Souverains
1. **Autorité Suprême** : Le backend E-ZZIO est l'unique source de vérité. L'UI est un visualiseur et un émetteur d'actions, elle ne peut court-circuiter aucune règle.
2. **Confinement `CapabilityPolicy`** : Toutes les actions des agents (y compris les requêtes émises depuis l'UI via `/master/chat`) passent impérativement par `CapabilityPolicy.evaluate_scope(...)`.
3. **Principe HITL** : Toute action mutatrice ou externe (`drive.write`, `github.push`, `system.destroy`, etc.) déclenche une mise en attente `REQUIRE_HUMAN`, génère un `approval_id`, bloque l'agent dans l'état `WAITING_APPROVAL` et alerte l'opérateur sur l'UI avec compte à rebours TTL.

---

## 2. TOPOLOGIE DES 8 ZONES (ROOMS) DE L'AI OFFICE

| Pièce (`room`) | Rôle & Spécialité | Agents Affectés | Capacités & Outils |
| :--- | :--- | :--- | :--- |
| **`command_center`** | Supervision générale, gouvernance suprême, routage des modèles | 👑 **E-ZZIO Master** | `CapabilityPolicy`, `AuditLedger`, `ModelRouter` |
| **`dev_lab`** | Développement autonome, génération de patches, subagent MCP | 🧑‍💻 **Alpha Coder**<br>🤖 **Hermes Subagent**<br>🛰️ **Antigravity** | `python`, `git`, `hermes_mcp_gateway`, `patch_parser` |
| **`research_room`** | Inspection forensique, crawling, analyse de surface d'outils | 🔬 **Scout Researcher** | `web.search`, `crawl4ai`, `ast_grep` |
| **`test_lab`** | Exécution des tests de non-régression, compilation | 🧪 **Sentinel QA** | `pytest`, `py_compile`, `sqlite_verifier` |
| **`security_vault`** | Intégrité cryptographique, scellement SHA-256, politique de sécurité | 🛡️ **Aegis Guard** | `AuditLedger`, `CapabilityPolicy`, `SecretsVault` |
| **`docs_room`** | Documentation technique vivante, synchronisation des specs | 📜 **Chronicle Scribe** | `doc_writer`, `markdown_validator` |
| **`devops_dock`** | Passerelle MCP, dispatch des fédérations de modèles | 🚀 **Nexus DevOps** | `fastapi`, `hermes_mcp_gateway`, `sse_bus` |
| **`memory_core`** | Persistance SQLite WAL, recherche sémantique FTS5 | 🧠 **Mnemosyne Memory** | `sqlite_wal`, `fts5`, `vector_cache` |

---

## 3. CONTRAT DE TÉLÉMÉTRIE & API EN DIRECT

### 3.1 `GET /master/api/v1/office/state`
Fournit la photographie consolidée en temps réel :
- `summary` : décompte des agents par état, santé des 4 providers, statut du Frozen Core (`INTACT`).
- `rooms` : liste des 8 pièces canoniques.
- `agents` : tableau des 10 agents souverains avec :
  - `agent_id`, `name`, `role`, `room`
  - `status` : `WORKING`, `WAITING_APPROVAL`, `DONE`, `IDLE`, `ERROR`
  - `progress` : progression réelle 0-100%
  - `current_action` : libellé de l'action en cours
  - `bubble` : bulle de pensée contextuelle en direct
  - `collaborator_id` : agent partenaire temporaire
  - `code_activity` : détails git (repo, commit, branch, fichier actif)
  - `terminal_logs` : sorties shell réelles de l'agent
  - `model` & `provider` : moteur LLM assigné
  - `is_master` & `parent_id` : hiérarchie parent/enfant (ex: Hermes sous Coder)
  - `tools` : liste des capacités déclarées

### 3.2 `GET /master/api/v1/office/events`
Fournit le flux des événements récents consolidés depuis l'`AuditLedger` immuable.

### 3.3 Machine à États Visuelle (Mapping Backend → UI)

```text
Backend TaskState / ApprovalStatus       Visual Status         Visual Animation
────────────────────────────────────────────────────────────────────────────────
RUNNING / BUSY                   ───►   WORKING         ───►  Bobbing, Typing Indicator
AWAITING_APPROVAL / PENDING      ───►   WAITING_APPROVAL───►  Glow Red, Pulsing Ring, Alert Banner
SUCCEEDED / COMPLETED            ───►   DONE            ───►  Emerald Status
FAILED / ERROR                   ───►   ERROR           ───►  Amber Status, Static Halt
BLOCKED_BY_EXTERNAL_QUOTA        ───►   ERROR (BLOCKED) ───►  Fail-safe Standby
```

### 3.4 Modèle de Sécurité & Non-Bypass
- L'UI ne communique qu'avec l'API REST FastAPI (`/master/api/v1/*`).
- Les requêtes de décision d'approbation (`POST /decide`) requièrent impérativement un `approval_id` existant et valide en base SQLite.
- Aucun jeton ou credential d'API n'est renvoyé au navigateur.
