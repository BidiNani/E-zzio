# E-ZZIO V7.11.2.4 — Active Runtime Source Locator Report
**Date :** 2026-08-11T17:22:57.340401

## 1. Localisation Physique Globale des 10 Modules Cibles
| Fichier Cible | Emplacements Trouvés sur le Disque (Chemin & Zone) |
| :--- | :--- |
| `contracts.py` | `runtime/action/contracts.py` *(ACTIVE_OTHER)*<br>`runtime/agent/contracts.py` *(ACTIVE_OTHER)*<br>`runtime/memory/semantic/contracts.py` *(ACTIVE_OTHER)*<br>`runtime/recovery/contracts.py` *(RECOVERY_TARGET_ZONE)* |
| `policies.py` | `runtime/recovery/decision/policies.py` *(RECOVERY_TARGET_ZONE)* |
| `governor.py` | `core/governor.py` *(ACTIVE_OTHER)*<br>`runtime/execution/governor.py` *(ACTIVE_OTHER)*<br>`runtime/hardware/ryzen_optimizer/governor.py` *(ACTIVE_OTHER)*<br>`runtime/recovery/decision/governor.py` *(RECOVERY_TARGET_ZONE)* |
| `manager.py` | `runtime/budget/manager.py` *(ACTIVE_OTHER)*<br>`runtime/recovery/rollback/manager.py` *(RECOVERY_TARGET_ZONE)* |
| `ledger.py` | `runtime/execution/ledger.py` *(ACTIVE_OTHER)*<br>`runtime/hardware/evidence/ledger.py` *(ACTIVE_OTHER)*<br>`runtime/recovery/ledger.py` *(RECOVERY_TARGET_ZONE)* |
| `quarantine.py` | `runtime/recovery/executor/quarantine.py` *(QUARANTINE)* |
| `scaling.py` | `runtime/recovery/executor/scaling.py` *(RECOVERY_TARGET_ZONE)* |
| `retry.py` | `runtime/agent/retry.py` *(ACTIVE_OTHER)*<br>`runtime/recovery/executor/retry.py` *(RECOVERY_TARGET_ZONE)* |
| `collector.py` | `runtime/hardware/trust/execution/attestation/collector.py` *(TEST)*<br>`runtime/incidents/collector.py` *(ACTIVE_OTHER)*<br>`runtime/rss/collector.py` *(ACTIVE_OTHER)*<br>`runtime/telemetry/collector.py` *(RECOVERY_TARGET_ZONE)* |
| `events.py` | `runtime/audit/events.py` *(ACTIVE_OTHER)*<br>`runtime/cognition/events.py` *(ACTIVE_OTHER)*<br>`runtime/core/events.py` *(ACTIVE_OTHER)*<br>`runtime/memory/events.py` *(ACTIVE_OTHER)*<br>`runtime/telemetry/events.py` *(RECOVERY_TARGET_ZONE)* |

## 2. Conclusion du Diagnostic Global
Ce balayage exhaustif permet de trancher définitivement : soit les fichiers résident dans une zone inattendue (archives profondes, sous un autre nom), soit ils ont totalement disparu du dépôt physique et constituaient une dépendance fantôme.

**Rapport JSON :** `source_locator_results.json`