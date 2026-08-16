# E-ZZIO V7.11.2.3 — Recovery Restore Plan Report
**Date :** 2026-08-11T17:20:32.758287
**Éléments identifiés pour restauration :** `23`

## 1. Matrice de Restauration (Quarantaine → Active)
| Module / Symbole | Présent en Quarantaine ? | Cible Active | Statut de l'Opération |
| :--- | :---: | :--- | :--- |
| `json` | ❌ Introuvable | `json.py` | **MANUAL_CHECK_REQUIRED** |
| `sqlite3` | ❌ Introuvable | `sqlite3.py` | **MANUAL_CHECK_REQUIRED** |
| `threading` | ❌ Introuvable | `threading.py` | **MANUAL_CHECK_REQUIRED** |
| `uuid` | ❌ Introuvable | `uuid.py` | **MANUAL_CHECK_REQUIRED** |
| `typing.Dict` | ❌ Introuvable | `typing/Dict.py` | **MANUAL_CHECK_REQUIRED** |
| `typing.Any` | ❌ Introuvable | `typing/Any.py` | **MANUAL_CHECK_REQUIRED** |
| `typing.Optional` | ❌ Introuvable | `typing/Optional.py` | **MANUAL_CHECK_REQUIRED** |
| `datetime.datetime` | ❌ Introuvable | `datetime/datetime.py` | **MANUAL_CHECK_REQUIRED** |
| `datetime.timezone` | ❌ Introuvable | `datetime/timezone.py` | **MANUAL_CHECK_REQUIRED** |
| `runtime.recovery.contracts.IncidentBundle` | ❌ Introuvable | `runtime/recovery/contracts/IncidentBundle.py` | **MANUAL_CHECK_REQUIRED** |
| `runtime.recovery.contracts.compute_decision_signature` | ❌ Introuvable | `runtime/recovery/contracts/compute_decision_signature.py` | **MANUAL_CHECK_REQUIRED** |
| `runtime.recovery.contracts.get_recovery_secret` | ❌ Introuvable | `runtime/recovery/contracts/get_recovery_secret.py` | **MANUAL_CHECK_REQUIRED** |
| `runtime.recovery.decision.policies.RecoveryPolicyEngine` | ❌ Introuvable | `runtime/recovery/decision/policies/RecoveryPolicyEngine.py` | **MANUAL_CHECK_REQUIRED** |
| `runtime.recovery.decision.governor.DecisionGovernor` | ❌ Introuvable | `runtime/recovery/decision/governor/DecisionGovernor.py` | **MANUAL_CHECK_REQUIRED** |
| `runtime.recovery.decision.governor.ExecutionApproval` | ❌ Introuvable | `runtime/recovery/decision/governor/ExecutionApproval.py` | **MANUAL_CHECK_REQUIRED** |
| `runtime.recovery.rollback.manager.RollbackManager` | ❌ Introuvable | `runtime/recovery/rollback/manager/RollbackManager.py` | **MANUAL_CHECK_REQUIRED** |
| `runtime.recovery.ledger.RecoveryLedger` | ❌ Introuvable | `runtime/recovery/ledger/RecoveryLedger.py` | **MANUAL_CHECK_REQUIRED** |
| `runtime.recovery.executor.quarantine.QuarantineExecutor` | ❌ Introuvable | `runtime/recovery/executor/quarantine/QuarantineExecutor.py` | **MANUAL_CHECK_REQUIRED** |
| `runtime.recovery.executor.scaling.ScalingExecutor` | ❌ Introuvable | `runtime/recovery/executor/scaling/ScalingExecutor.py` | **MANUAL_CHECK_REQUIRED** |
| `runtime.recovery.executor.retry.RetryExecutor` | ❌ Introuvable | `runtime/recovery/executor/retry/RetryExecutor.py` | **MANUAL_CHECK_REQUIRED** |
| `runtime.telemetry.collector.TelemetryCollector` | ❌ Introuvable | `runtime/telemetry/collector/TelemetryCollector.py` | **MANUAL_CHECK_REQUIRED** |
| `runtime.telemetry.events.TelemetryEvent` | ❌ Introuvable | `runtime/telemetry/events/TelemetryEvent.py` | **MANUAL_CHECK_REQUIRED** |
| `runtime.telemetry.events.EventType` | ❌ Introuvable | `runtime/telemetry/events/EventType.py` | **MANUAL_CHECK_REQUIRED** |

## 2. Conclusion du Planificateur
Ce plan garantit qu'aucune réécriture de code n'est nécessaire. Les modules indispensables à engine.py seront replacés à l'identique depuis la quarantaine sous contrôle d'intégrité SHA-256.

**Rapport JSON :** `recovery_restore_plan.json`