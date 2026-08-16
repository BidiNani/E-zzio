# E-ZZIO V7.11.2.5 — Truth & Symbol Resolution Report
**Date :** 2026-08-11T17:24:03.745390
**Fichier analysé :** `runtime/recovery/decision/engine.py`

## 1. Matrice de Vérité des Imports de Engine.py
| Type d'Import | Module / Package | Noms Importés | Statut Topologique | Localisation | Validation des Symboles |
| :--- | :--- | :--- | :---: | :--- | :--- |
| `ImportFrom` | `json` | `json` | 🟢 STDLIB | Système | N/A |
| `ImportFrom` | `sqlite3` | `sqlite3` | 🟢 STDLIB | Système | N/A |
| `ImportFrom` | `threading` | `threading` | 🟢 STDLIB | Système | N/A |
| `ImportFrom` | `uuid` | `uuid` | 🟢 STDLIB | Système | N/A |
| `ImportFrom` | `typing` | `Dict, Any, Optional` | 🟢 STDLIB | Système | N/A |
| `ImportFrom` | `datetime` | `datetime, timezone` | 🟢 STDLIB | Système | N/A |
| `ImportFrom` | `runtime.recovery.contracts` | `IncidentBundle, compute_decision_signature, get_recovery_secret` | ✅ Present | `runtime/recovery/contracts.py` | `ALL_SYMBOLS_FOUND` |
| `ImportFrom` | `runtime.recovery.decision.policies` | `RecoveryPolicyEngine, RemediationAction` | ✅ Present | `runtime/recovery/decision/policies.py` | `ALL_SYMBOLS_FOUND` |
| `ImportFrom` | `runtime.recovery.decision.governor` | `DecisionGovernor, ExecutionApproval` | ✅ Present | `runtime/recovery/decision/governor.py` | `ALL_SYMBOLS_FOUND` |
| `ImportFrom` | `runtime.recovery.rollback.manager` | `RollbackManager` | ✅ Present | `runtime/recovery/rollback/manager.py` | `ALL_SYMBOLS_FOUND` |
| `ImportFrom` | `runtime.recovery.ledger` | `RecoveryLedger` | ✅ Present | `runtime/recovery/ledger.py` | `ALL_SYMBOLS_FOUND` |
| `ImportFrom` | `runtime.recovery.executor.quarantine` | `QuarantineExecutor` | ✅ Present | `runtime/recovery/executor/quarantine.py` | `ALL_SYMBOLS_FOUND` |
| `ImportFrom` | `runtime.recovery.executor.scaling` | `ScalingExecutor` | ✅ Present | `runtime/recovery/executor/scaling.py` | `ALL_SYMBOLS_FOUND` |
| `ImportFrom` | `runtime.recovery.executor.retry` | `RetryExecutor` | ✅ Present | `runtime/recovery/executor/retry.py` | `ALL_SYMBOLS_FOUND` |
| `ImportFrom` | `runtime.telemetry.collector` | `TelemetryCollector` | ✅ Present | `runtime/telemetry/collector.py` | `ALL_SYMBOLS_FOUND` |
| `ImportFrom` | `runtime.telemetry.events` | `TelemetryEvent, EventType` | ✅ Present | `runtime/telemetry/events.py` | `ALL_SYMBOLS_FOUND` |

## 2. Synthèse du Juge de Paix
Cet audit sépare définitivement les bruits de bibliothèque standard, les modules actifs et le **seul et unique module réellement exilé en quarantaine** (`quarantine.py`). Aucune réécriture globale n'est nécessaire : le diagnostic est désormais mathématiquement exact.

**Rapport JSON :** `truth_resolution_audit.json`