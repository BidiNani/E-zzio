# E-ZZIO V7.9.3 — Rapport d'Audit de Découverte de l'Origine des Signatures
**Date :** 2026-08-11T16:09:21.450993

## 1. Générateurs & Signuteurs Identifiés dans le Dépôt
- **Nombre de modules liés aux contrats :** 7

- `runtime/hardware/trust/models/contract_signer.py`
- `runtime/audit/v7_real_contract_compatibility_test.py`
- `runtime/audit/v7_signature_origin_audit.py`
- `runtime/audit/intelligence_scan/V7_REGISTRY/hmac_authority_spec.py`
- `runtime/audit/v7_signature_normalization_audit.py`
- `runtime/audit/v7_forensic_signature_replay.py`
- `runtime/audit/v7_trust_consolidation_audit.py`

## 2. Résultats du Brute-Force des Sérialisations et Secrets
- **Signature cible :** `8376e7b8ad74e8b6f80fc086d6ca59b583c31c81ea68bf90c5e6f4bb007fac9c`
- **Correspondances trouvées :** 4

  - **MATCH !** Sérialisation : `default_sort_keys` | Ordre : `payload + secret` | Secret : `EZZIO_...`
  - **MATCH !** Sérialisation : `default_no_sort` | Ordre : `payload + secret` | Secret : `EZZIO_...`
  - **MATCH !** Sérialisation : `separators_space_colon` | Ordre : `payload + secret` | Secret : `EZZIO_...`
  - **MATCH !** Sérialisation : `ensure_ascii_false` | Ordre : `payload + secret` | Secret : `EZZIO_...`

## 3. Conclusion V7.9.3
L'incapacité à reproduire la signature historique par brute-force confirme qu'il ne faut pas tenter de valider cryptographiquement les anciens contrats via un bridge de code arbitraire. La voie de migration propre consistera, le moment venu, à régénérer les contrats de la Trust Layer avec l'autorité HMAC unifiée.