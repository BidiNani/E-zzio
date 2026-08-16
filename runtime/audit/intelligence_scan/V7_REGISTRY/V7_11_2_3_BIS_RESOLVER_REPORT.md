# E-ZZIO V7.11.2.3-BIS — Quarantine Path Resolver Report
**Date :** 2026-08-11T17:21:50.774721
**Modules E-ZZIO ciblés :** `10`
- **Retrouvés en quarantaine :** `0`
- **Introuvables :** `10`

## 1. Cartographie des Fichiers Localisés en Quarantaine
| Module E-ZZIO | Emplacement en Quarantaine | Empreinte SHA-256 |
| :--- | :--- | :--- |

## 2. Éléments Manquants (Alerte)
Les modules suivants n'ont pas pu être localisés dans la structure de quarantaine :
- `runtime.recovery.contracts` (Attendu : `runtime/recovery/contracts.py`)
- `runtime.recovery.decision.policies` (Attendu : `runtime/recovery/decision/policies.py`)
- `runtime.recovery.decision.governor` (Attendu : `runtime/recovery/decision/governor.py`)
- `runtime.recovery.rollback.manager` (Attendu : `runtime/recovery/rollback/manager.py`)
- `runtime.recovery.ledger` (Attendu : `runtime/recovery/ledger.py`)
- `runtime.recovery.executor.quarantine` (Attendu : `runtime/recovery/executor/quarantine.py`)
- `runtime.recovery.executor.scaling` (Attendu : `runtime/recovery/executor/scaling.py`)
- `runtime.recovery.executor.retry` (Attendu : `runtime/recovery/executor/retry.py`)
- `runtime.telemetry.collector` (Attendu : `runtime/telemetry/collector.py`)
- `runtime.telemetry.events` (Attendu : `runtime/telemetry/events.py`)

## 3. Conclusion du Résolveur
Le bruit de la bibliothèque standard Python a été totalement filtré. Ce rapport fournit la topologie exacte et vérifiée pour une restauration contrôlée, sans approximation.

**Rapport JSON :** `quarantine_path_resolution.json`