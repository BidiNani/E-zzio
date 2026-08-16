# E-ZZIO V7.11.5.6 — Consumer Contract Alignment Audit Report
**Date :** 2026-08-11T17:46:07.770863

## 1. Inspection des Appels Consommateurs (Arguments Fournis vs V3)
Analyse AST détaillée des paramètres passés aux classes du noyau par les points d'entrée actifs :
### 📄 `runtime/gateway/adapter.py` *(Présent: True)*
- Ligne **59** : ` IncidentBundle ` | Args positionnels: `0` | Mots-clés fournis: `[incident_id, timestamp, severity, severity_score, category, execution_id, action_name, trace_id, span_id, state_trace, context_signature_valid, payload_hash, bundle_hash, telemetry_snapshot, findings, root_candidates, metadata]`

### 📄 `runtime/recovery/incident_bundle.py` *(Présent: True)*
- Ligne **79** : ` IncidentBundle ` | Args positionnels: `0` | Mots-clés fournis: `[incident_id, timestamp, severity, severity_score, category, execution_id, action_name, trace_id, span_id, state_trace, context_signature_valid, payload_hash, bundle_hash, telemetry_snapshot, findings, root_candidates, metadata]`
- Ligne **102** : ` IncidentBundle ` | Args positionnels: `0` | Mots-clés fournis: `[incident_id, timestamp, severity, severity_score, category, execution_id, action_name, trace_id, span_id, state_trace, context_signature_valid, payload_hash, bundle_hash, telemetry_snapshot, findings, root_candidates, metadata]`
- Ligne **18** : ` TelemetryCollector ` | Args positionnels: `0` | Mots-clés fournis: `[Aucun (appel positionnel pur)]`
- Ligne **126** : ` TelemetryEvent ` | Args positionnels: `0` | Mots-clés fournis: `[event_type, payload]`

### 📄 `runtime/recovery/queue/bus.py` *(Présent: True)*
- Ligne **97** : ` IncidentBundle ` | Args positionnels: `0` | Mots-clés fournis: `[incident_id, timestamp, severity, severity_score, category, execution_id, action_name, trace_id, span_id, state_trace, context_signature_valid, payload_hash, bundle_hash, telemetry_snapshot, findings, root_candidates, metadata]`

### 📄 `runtime/recovery/decision/engine.py` *(Présent: True)*
- Ligne **32** : ` RecoveryPolicyEngine ` | Args positionnels: `0` | Mots-clés fournis: `[Aucun (appel positionnel pur)]`
- Ligne **36** : ` TelemetryCollector ` | Args positionnels: `0` | Mots-clés fournis: `[Aucun (appel positionnel pur)]`
- Ligne **165** : ` TelemetryEvent ` | Args positionnels: `0` | Mots-clés fournis: `[event_type, payload]`

## 2. Conclusion de l'Audit d'Alignement
Ce rapport fournit la cartographie exacte des divergences d'arguments, permettant de rédiger les correctifs ciblés (mise à jour des appels vers les contrats V3 sans altérer la baseline).

**Registre JSON :** `consumer_alignment_audit.json`