# E-ZZIO V7.11.2.2 — Symbol Usage & Dead Import Analyzer
**Date :** 2026-08-11T17:19:21.027681
**Fichier cible :** `runtime/recovery/decision/engine.py`

## 1. Matrice d'Usage des Imports
| Symbole / Module | Ligne | Utilisé dans le code ? | Fichier physique présent ? | Statut architectural |
| :--- | :---: | :---: | :---: | :--- |
| `json` | 1 | ✅ Oui | ⚠️ Absent / Quarantaine | **BROKEN_IMPORT (Critique)** |
| `sqlite3` | 2 | ✅ Oui | ⚠️ Absent / Quarantaine | **BROKEN_IMPORT (Critique)** |
| `threading` | 3 | ✅ Oui | ⚠️ Absent / Quarantaine | **BROKEN_IMPORT (Critique)** |
| `uuid` | 4 | ✅ Oui | ⚠️ Absent / Quarantaine | **BROKEN_IMPORT (Critique)** |
| `typing.Dict` | 5 | ✅ Oui | ⚠️ Absent / Quarantaine | **BROKEN_IMPORT (Critique)** |
| `typing.Any` | 5 | ✅ Oui | ⚠️ Absent / Quarantaine | **BROKEN_IMPORT (Critique)** |
| `typing.Optional` | 5 | ✅ Oui | ⚠️ Absent / Quarantaine | **BROKEN_IMPORT (Critique)** |
| `datetime.datetime` | 6 | ✅ Oui | ⚠️ Absent / Quarantaine | **BROKEN_IMPORT (Critique)** |
| `datetime.timezone` | 6 | ✅ Oui | ⚠️ Absent / Quarantaine | **BROKEN_IMPORT (Critique)** |
| `runtime.recovery.contracts.IncidentBundle` | 8 | ✅ Oui | ⚠️ Absent / Quarantaine | **BROKEN_IMPORT (Critique)** |
| `runtime.recovery.contracts.compute_decision_signature` | 8 | ✅ Oui | ⚠️ Absent / Quarantaine | **BROKEN_IMPORT (Critique)** |
| `runtime.recovery.contracts.get_recovery_secret` | 8 | ✅ Oui | ⚠️ Absent / Quarantaine | **BROKEN_IMPORT (Critique)** |
| `runtime.recovery.decision.policies.RecoveryPolicyEngine` | 9 | ✅ Oui | ⚠️ Absent / Quarantaine | **BROKEN_IMPORT (Critique)** |
| `runtime.recovery.decision.policies.RemediationAction` | 9 | ❌ Non (Mort) | ⚠️ Absent / Quarantaine | **DEAD_IMPORT (À purger)** |
| `runtime.recovery.decision.governor.DecisionGovernor` | 10 | ✅ Oui | ⚠️ Absent / Quarantaine | **BROKEN_IMPORT (Critique)** |
| `runtime.recovery.decision.governor.ExecutionApproval` | 10 | ✅ Oui | ⚠️ Absent / Quarantaine | **BROKEN_IMPORT (Critique)** |
| `runtime.recovery.rollback.manager.RollbackManager` | 11 | ✅ Oui | ⚠️ Absent / Quarantaine | **BROKEN_IMPORT (Critique)** |
| `runtime.recovery.ledger.RecoveryLedger` | 12 | ✅ Oui | ⚠️ Absent / Quarantaine | **BROKEN_IMPORT (Critique)** |
| `runtime.recovery.executor.quarantine.QuarantineExecutor` | 13 | ✅ Oui | ⚠️ Absent / Quarantaine | **BROKEN_IMPORT (Critique)** |
| `runtime.recovery.executor.scaling.ScalingExecutor` | 14 | ✅ Oui | ⚠️ Absent / Quarantaine | **BROKEN_IMPORT (Critique)** |
| `runtime.recovery.executor.retry.RetryExecutor` | 15 | ✅ Oui | ⚠️ Absent / Quarantaine | **BROKEN_IMPORT (Critique)** |
| `runtime.telemetry.collector.TelemetryCollector` | 16 | ✅ Oui | ⚠️ Absent / Quarantaine | **BROKEN_IMPORT (Critique)** |
| `runtime.telemetry.events.TelemetryEvent` | 17 | ✅ Oui | ⚠️ Absent / Quarantaine | **BROKEN_IMPORT (Critique)** |
| `runtime.telemetry.events.EventType` | 17 | ✅ Oui | ⚠️ Absent / Quarantaine | **BROKEN_IMPORT (Critique)** |

## 2. Conclusion de l'Analyse d'Usage
Cette matrice sépare définitivement les imports fonctionnels des vestiges historiques. Tout import marqué `DEAD_IMPORT` peut être supprimé sans risque pour la logique d'exécution.

**Rapport JSON :** `symbol_usage_analysis.json`