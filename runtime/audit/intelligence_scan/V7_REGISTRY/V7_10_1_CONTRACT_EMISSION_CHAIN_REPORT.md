# E-ZZIO V7.10.1 — Contract Emission Chain Report
**Date :** 2026-08-11T16:20:12.004166

## 1. Analyse des Chaînes d'Instanciation et d'Émission
**Modules impliquant ContractSigner ou des méthodes de signature :** 16

### Fichier : `runtime/audit/v7_contract_birth_trace.py`
  - **Méthodes détectées :**
    - Ligne 75 : `write_text`
    - Ligne 118 : `write_text`

### Fichier : `runtime/audit/v7_contract_emission_chain.py`
  - **Méthodes détectées :**
    - Ligne 77 : `write_text`
    - Ligne 113 : `write_text`

### Fichier : `runtime/audit/v7_contract_generation_trace.py`
  - **Méthodes détectées :**
    - Ligne 56 : `scan_writers_and_generators`
    - Ligne 66 : `write_text`
    - Ligne 101 : `write_text`

### Fichier : `runtime/audit/v7_contract_inspector.py`
  - **Méthodes détectées :**
    - Ligne 48 : `write_text`
    - Ligne 95 : `write_text`

### Fichier : `runtime/audit/v7_contract_simulation.py`
  - **Méthodes détectées :**
    - Ligne 115 : `write_text`
    - Ligne 152 : `write_text`

### Fichier : `runtime/audit/v7_cryptographic_evidence_bundle.py`
  - **Méthodes détectées :**
    - Ligne 86 : `write_text`
    - Ligne 127 : `write_text`

### Fichier : `runtime/audit/v7_evidence_reconciliation.py`
  - **Méthodes détectées :**
    - Ligne 67 : `write_text`
    - Ligne 94 : `write_text`

### Fichier : `runtime/audit/v7_execution_trace.py`
  - **Méthodes détectées :**
    - Ligne 69 : `inspect_contract_signer_internals`
    - Ligne 70 : `find_contract_signer_callers`
    - Ligne 79 : `write_text`
    - Ligne 119 : `write_text`

### Fichier : `runtime/audit/v7_forensic_signature_replay.py`
  - **Méthodes détectées :**
    - Ligne 94 : `write_text`
    - Ligne 134 : `write_text`

### Fichier : `runtime/audit/v7_real_contract_compatibility_test.py`
  - **Méthodes détectées :**
    - Ligne 96 : `write_text`
    - Ligne 130 : `write_text`
    - Ligne 36 : `inspect_contract_signer_implementation`

### Fichier : `runtime/audit/v7_registry_audit.py`
  - **Méthodes détectées :**
    - Ligne 99 : `write_text`
    - Ligne 100 : `write_text`
    - Ligne 101 : `write_text`
    - Ligne 117 : `write_text`
    - Ligne 123 : `write_text`
    - Ligne 129 : `write_text`
    - Ligne 141 : `write_text`

### Fichier : `runtime/audit/v7_signature_archaeology.py`
  - **Méthodes détectées :**
    - Ligne 71 : `write_text`
    - Ligne 124 : `write_text`
    - Ligne 128 : `run_signature_archaeology`

### Fichier : `runtime/audit/v7_signature_origin_audit.py`
  - **Méthodes détectées :**
    - Ligne 114 : `write_text`
    - Ligne 154 : `write_text`

### Fichier : `runtime/audit/v7_signature_provenance_audit.py`
  - **Méthodes détectées :**
    - Ligne 88 : `write_text`
    - Ligne 133 : `write_text`

### Fichier : `runtime/audit/v7_trust_consolidation_audit.py`
  - **Méthodes détectées :**
    - Ligne 61 : `write_text`
    - Ligne 94 : `write_text`

### Fichier : `runtime/hardware/trust/models/contract_signer.py`
  - **Instanciations / Appels ciblés :**
    - Ligne 34 : `ContractSigner(args=[])`
  - **Méthodes détectées :**
    - Ligne 35 : `sign_file`


## 2. Statut de la Migration Trust
**MIGRATION BLOQUÉE :** Cet audit complète la cartographie des appelants. Tant que le contexte exact d'écriture du fichier `qwen2.5-7b.contract.json` n'est pas formellement relié à un flux d'exécution traçable, aucune altération de la Trust Layer n'est permise.