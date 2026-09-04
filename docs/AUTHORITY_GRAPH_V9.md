# E-ZZIO V9.0 — AUTHORITY GRAPH

Ce document définit la matrice d'autorité unique et sans équivoque d'E-ZZIO.
**Règle absolue : UNE SEULE AUTORITÉ PAR DOMAINE.**

---

## 1. GRAPHE DES AUTORITÉS MAJEURES

```text
                        ┌────────────────────────┐
                        │   ENTRY POINT (HTTP)   │
                        │    web_server.py:8001  │
                        └───────────┬────────────┘
                                    │
                        ┌───────────▼────────────┐
                        │  COGNITIVE ORCHESTRATION│
                        │    CognitiveGateway    │
                        └───────────┬────────────┘
                                    │
                        ┌───────────▼────────────┐
                        │ MODEL STRATEGY PROFILE │
                        │      ModelRouter       │
                        └───────────┬────────────┘
                                    │
                 ┌──────────────────┴──────────────────┐
                 │                                     │
    ┌────────────▼────────────┐            ┌───────────▼────────────┐
    │ GEMINI INFRA & QUOTAS   │            │   SECONDARY FALLBACK   │
    │      GeminiPool         │            │     OllamaProvider     │
    └────────────┬────────────┘            └────────────────────────┘
                 │
    ┌────────────▼────────────┐
    │ GEMINI CLOUD TRANSPORT  │
    │     GeminiProvider      │
    └─────────────────────────┘
```

---

## 2. MATRICE « QUI DÉCIDE, QUI EXÉCUTE, QUI STOCKES, QUI AUTORISE, QUI OBSERVE »

| Domaine | Qui Décide ? | Qui Exécute ? | Qui Stocke ? | Qui Autorise ? | Qui Observe ? |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **Cognition & LLM** | `ModelRouter` | `GeminiProvider` / `OllamaProvider` | `UnifiedMemoryGateway` | `CapabilityPolicy` | `AuditLedger` + OpenTelemetry |
| **Quotas & Projets** | `GeminiPoolManager` | `GeminiPool.get_client()` | In-Memory Pool State | `GeminiPool` | `provider_events.db` |
| **Capacités & Outils** | `CapabilityRegistry` | Connecteur Direct (`github`, etc.) | `UnifiedMemoryGateway` | `CapabilityPolicy` | `AuditLedger` |
| **Mémoire & Sessions** | `UnifiedMemoryGateway` | `aiosqlite` WAL | `unified_memory.db` | `CapabilityPolicy` | OpenTelemetry |
| **Coding & Self-Healing** | `CodingAgentHarness` | `CodingAgentHarness.run_loop` | Disque Workspace | `CapabilityPolicy` | `AuditLedger` |
| **Sécurité & Secrets** | `CapabilityPolicy` | `UnifiedVault` | `secrets_vault` AES-GCM | `CapabilityPolicy` | `AuditLedger` |
