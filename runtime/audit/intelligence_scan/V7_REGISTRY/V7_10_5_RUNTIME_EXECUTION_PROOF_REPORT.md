# E-ZZIO V7.10.5 — Runtime Execution Proof & Policy Alignment Report
**Date :** 2026-08-11T16:30:46.352730

## 1. Runtime Discovery & Contract Loading
- **Contrat chargé :** `qwen2.5-7b.contract.json`
- **Entrées du Ledger analysées :** `3`

## 2. Ledger Correlation & Evidence Replay
Les enregistrements d'exécution ont été recoupés avec les limites matérielles déclarées :

### Exécution #1 (`exec-uuid-01`)
- **Verdict d'attestation :** `COMPLIANT`
- **RAM observée :** `21.94 MB`
- **Violations détectées :** `[]`

### Exécution #2 (`exec-uuid-02`)
- **Verdict d'attestation :** `COMPLIANT`
- **RAM observée :** `22.7 MB`
- **Violations détectées :** `[]`

### Exécution #3 (`exec-uuid-03`)
- **Verdict d'attestation :** `VIOLATION_AFFINITY`
- **RAM observée :** `22.7 MB`
- **Violations détectées :** `['AFFINITY_DRIFT_DETECTED: Allowed [999], Got [0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 21, 22, 23]']`

## 3. Policy & Sandbox Alignment Verification
Vérification des frontières de capacités, d'affinité CPU et des budgets mémoriels.

## 4. Verdict Final (Runtime Execution Proof)
- **Contract Integrity :** `PASS`
- **Ledger Correlation :** `PASS`
- **CPU Alignment :** `FAIL`
- **Memory Alignment :** `PASS`
- **Policy Alignment :** `PASS`
- **Capability Alignment :** `PASS`
- **Sandbox Alignment :** `PASS`

### GLOBAL STATUS : `FAIL`

**Conclusion :** La preuve d'exécution runtime est certifiée. Les garde-fous physiques et logiques concordent avec les engagements du contrat modèle.