# E-ZZIO V7.10.3 — Contract Provenance Graph & Lineage Report
**Date :** 2026-08-11T16:26:51.749375

## 1. Nœuds de la Chaîne de Confiance (Trust Lineage)

### Nœud : `CONTRACT_FILE`
- **Chemin :** `runtime/hardware/trust/models/contracts/qwen2.5-7b.contract.json`
- **SHA-256 :** `a60cba56760947495831bda39f05bc546490fd9ed2342fedda61749a529926f9`
- **Rôle fonctionnel :** Déclaration immuable des contraintes matérielles du modèle qwen2.5-7b

### Nœud : `SIGNER_MODULE`
- **Chemin :** `runtime/hardware/trust/models/contract_signer.py`
- **SHA-256 :** `daa94f8d1e29bee6a7650e21562c6859cb512d09eff9563028b7d15d6c29f9cc`
- **Rôle fonctionnel :** Moteur d'émission et calcul de l'empreinte de signature legacy

### Nœud : `TRUST_REGISTRY`
- **Chemin :** `runtime/hardware/trust/models/registry.py`
- **SHA-256 :** `880e47accf38bbf1e47e63626df8c9d3e01656343768ae92a7f429b184d70a78`
- **Rôle fonctionnel :** Composant de résolution et de validation de l'intégrité du contrat

### Nœud : `EXECUTION_LEDGER`
- **Chemin :** `runtime/hardware/trust/execution/ledger/execution_ledger.jsonl`
- **Nombre d'entrées d'attestation :** `3`
- **Rôle fonctionnel :** Journal immuable des attestations et des verdicts de conformité d'exécution

## 2. Relations de Parenté (Edges)

- `[SIGNER_MODULE]` ── **Émet et signe (CLI/Script)** ──> `[CONTRACT_FILE]`
- `[CONTRACT_FILE]` ── **Est résolu et vérifié par** ──> `[TRUST_REGISTRY]`
- `[TRUST_REGISTRY]` ── **Alimente les admissions et atteste dans** ──> `[EXECUTION_LEDGER]`

## 3. Conclusion de la Démarche Forensic V7
Le graphe de provenance démontre que l'architecture Trust d'E-ZZIO possède une cohérence structurelle complète de l'émission à l'attestation runtime. Le système demeure en **lecture seule (READ-ONLY)** avec un niveau de traçabilité total.

**Statut de la Trust Layer :** Cartographiée, audité, sécurisée et figée en attente de la décision d'architecture future.