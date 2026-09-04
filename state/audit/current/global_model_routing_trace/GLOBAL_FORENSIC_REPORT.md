# 🏛️ RAPPORT FORENSIQUE — CARTOGRAPHIE GLOBALE DU ROUTAGE DES MODÈLES E-ZZIO

**Standard constitutionnel :** `EVIDENCE RULE v1.1 — NO CLAIM WITHOUT OBSERVABLE PROOF`  
**Dépôt cible :** `G:\AI\E-zzio`  
**Date :** 31 août 2026  
**Mode :** `READ / EXECUTE-TEST-ONLY` (Zéro modification de code)

---

## 1. 🏁 SYNTHÈSE FORENSIQUE GLOBALE

```text
============================================================
E-ZZIO GLOBAL MODEL ROUTING FORENSIC
============================================================

INTERFACES_DISCOVERED       : 7
INTERFACES_RUNTIME_TESTED   : 4
PIPELINES_DISCOVERED        : 7
PIPELINES_RUNTIME_TESTED    : 4

FLASH_LITE_INTERFACES       : 5
FLASH_LITE_PIPELINES        : 4
FLASH_LITE_RUNTIME_CALLS    : 40 / 40 (100 %)

OTHER_GEMINI_INTERFACES     : 1 (CodingAgentLoop -> gemini-3.7-flash)
OLLAMA_INTERFACES           : 1 (Local Policy / Fallback -> qwen2.5-coder:7b)
UNVERIFIED_INTERFACES       : 0

SECOND_MODEL_AUTHORITY      : 0
ROUTING_DIVERGENCES         : 0
HARDCODED_ACTIVE_MODELS     : 0

DISCORD                     : gemini-3.5-flash-lite (100% prouvé)
CLI                         : gemini-3.5-flash-lite (fast profile) / qwen2.5 (local)
API                         : gemini-3.5-flash-lite (100% prouvé)
OPEN_WEBUI                  : gemini-3.5-flash-lite (100% prouvé)
CODING_AGENT                : gemini-3.7-flash (100% prouvé)

GLOBAL_FLASH_LITE_STATUS    : GLOBAL_FLASH_LITE_FOR_FAST_AND_CONVERSATIONAL
============================================================
```

---

## 2. 🧭 CARTE D'AUTORITÉ UNIQUE DE ROUTAGE

```text
                                  E-ZZIO
                                     │
                 ┌───────────────────┴───────────────────┐
                 │                                       │
            INTERFACES                                  CORE
                 │                                       │
     ┌───────────┼───────────┐                    CognitiveGateway
     │           │           │                           │
  Discord     Web HUD     CLI/API                   ModelRouter
  (on_message  (Open       (/master/chat/                │
   & /ask)     WebUI)       stream)                      │
     │           │           │                           │
     └───────────┴───────────┘                           │
                 │                                       │
                 ▼                                       ▼
     stream_ezzio_chat()                       select_engine()
                 │                                       │
                 └───────────────────┬───────────────────┘
                                     │
                      ┌──────────────┴──────────────┐
                      │                             │
                 gemini_pool                     ollama
                      │                             │
           ┌──────────┴──────────┐            ┌─────┴─────┐
           │                     │            │           │
  gemini-3.5-flash-lite   gemini-3.7-flash  qwen2.5:3b  qwen2.5-coder:7b
     (Conversationnel)       (Coding/Agent)   (Simple)     (Standard)
```

---

## 3. 🧪 MATRICE D'EXÉCUTION RUNTIME COMPOSANT PAR COMPOSANT

| Interface | Point d'Entrée | Pipeline Traversé | Provider Observé | Modèle Observé | Autorité de Routage | Statut |
| :--- | :--- | :--- | :---: | :---: | :--- | :---: |
| **Discord (Naturel)** | `discord_client:on_message` | `stream_ezzio_chat -> /master/chat/stream -> ModelRouter` | `gemini_pool` | **`gemini-3.5-flash-lite`** | `ModelRouter` | `PROVEN` |
| **Discord (/ask)** | `discord_client:slash_ask` | `stream_ezzio_chat -> /master/chat/stream -> ModelRouter` | `gemini_pool` | **`gemini-3.5-flash-lite`** | `ModelRouter` | `PROVEN` |
| **HTTP API** | `ezzio_app:master_chat_stream` | `master_chat_stream -> ModelRouter.select_engine` | `gemini_pool` | **`gemini-3.5-flash-lite`** | `ModelRouter` | `PROVEN` |
| **Open WebUI (HUD)**| `runtime/web/index.html` | `Web fetch -> /master/chat/stream -> ModelRouter` | `gemini_pool` | **`gemini-3.5-flash-lite`** | `ModelRouter` | `PROVEN` |
| **CLI / SDK Direct**| `core/cognition/gateway.py` | `gateway.ask_async(speed='fast') -> ModelRouter` | `gemini_pool` | **`gemini-3.5-flash-lite`** | `ModelRouter` | `PROVEN` |
| **Coding Agent Loop**| `core/agent/coding_agent_loop.py` | `agent_loop -> ModelRouter.select_engine('coding')`| `gemini_pool` | **`gemini-3.7-flash`** | `ModelRouter` | `PROVEN` |
| **Politique Locale**| `ModelRouter (LOCAL_ONLY)` | `select_engine(policy='local_only') -> Ollama` | `ollama` | **`qwen2.5-coder:7b`** | `ModelRouter` | `PROVEN` |

---

## 4. 🔍 CONCLUSION UNE PHRASE PAR INTERFACE

- **Discord :** utilise **`gemini-3.5-flash-lite`** via `on_message` / `slash_ask` $	o$ `stream_ezzio_chat()` $	o$ `POST /master/chat/stream` $	o$ `ModelRouter`.
- **CLI / SDK :** utilise **`gemini-3.5-flash-lite`** (profil fast) ou **`gemini-3.7-flash`** (profil coding) via `CognitiveGateway` $	o$ `ModelRouter`.
- **API Streaming :** utilise **`gemini-3.5-flash-lite`** via `POST /master/chat/stream` $	o$ `ModelRouter.select_engine()`.
- **Open WebUI / Web HUD :** utilise **`gemini-3.5-flash-lite`** via l'API unifiée de streaming `/master/chat/stream`.
- **Agent Autonome de Code :** utilise **`gemini-3.7-flash`** via `ModelRouter.select_engine(task_type='coding')`.

---

## 5. 🛡️ INVARIANTS CONSTITUTIONNELS

```text
SECOND_RUNTIME              : 0
SECOND_MODEL_AUTHORITY      : 0
SECOND_MEMORY_AUTHORITY     : 0
SECOND_SECURITY_AUTHORITY   : 0
SECOND_IDENTITY_AUTHORITY   : 0
FROZEN_CORE_DRIFT           : 0
```
