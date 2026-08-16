# E-ZZIO V7.11.5.1 — Behavioral Contract Diff & Forensics Report
**Date :** 2026-08-11T17:31:57.112990

## 1. Vérité des Signatures des Classes Cibles
Analyse par introspection des contrats réels exposés par le code de production :
### 📌 `runtime.recovery.contracts.IncidentBundle` *(Statut: SUCCESS)*
**Paramètres du constructeur (`__init__`) :**
- ` incident_id ` (Défaut: `REQUIRED`)
- ` timestamp ` (Défaut: `REQUIRED`)
- ` severity ` (Défaut: `REQUIRED`)
- ` severity_score ` (Défaut: `REQUIRED`)
- ` category ` (Défaut: `REQUIRED`)
- ` execution_id ` (Défaut: `REQUIRED`)
- ` action_name ` (Défaut: `REQUIRED`)
- ` trace_id ` (Défaut: `REQUIRED`)
- ` span_id ` (Défaut: `REQUIRED`)
- ` state_trace ` (Défaut: `REQUIRED`)
- ` context_signature_valid ` (Défaut: `REQUIRED`)
- ` payload_hash ` (Défaut: `REQUIRED`)
- ` bundle_hash ` (Défaut: `REQUIRED`)
- ` telemetry_snapshot ` (Défaut: `REQUIRED`)
- ` findings ` (Défaut: `REQUIRED`)
- ` root_candidates ` (Défaut: `REQUIRED`)
- ` metadata ` (Défaut: `<factory>`)

**Méthodes publiques disponibles :**
- `compute_canonical_hash()`
- `verify_integrity()`

### 📌 `runtime.telemetry.events.TelemetryEvent` *(Statut: SUCCESS)*
**Paramètres du constructeur (`__init__`) :**
- ` event_id ` (Défaut: `<factory>`)
- ` event_type ` (Défaut: `EventType.EXECUTION_COMPLETED`)
- ` timestamp ` (Défaut: `<factory>`)
- ` payload ` (Défaut: `<factory>`)

**Méthodes publiques disponibles :**
- *(Aucune méthode publique explicite hors constructeur)*

### 📌 `runtime.recovery.decision.policies.RecoveryPolicyEngine` *(Statut: SUCCESS)*
**Paramètres du constructeur (`__init__`) :**
- ` config_path ` (Défaut: `config/recovery_policy.json`)

**Méthodes publiques disponibles :**
- `evaluate()`

## 2. Conclusion de l'Analyse Forensique
Ce rapport expose la signature exacte attendue par chaque composant. Il servira de base de référence pour aligner proprement les tests comportementaux ou adapter les adaptateurs d'API sans toucher au cœur fonctionnel.

**Registre JSON brut :** `behavioral_symbols.json`