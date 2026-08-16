# E-ZZIO V7.5 — Rapport de Simulation de l'Autorité Contractuelle
**Date :** 2026-08-11T15:49:38.450566

## 1. Résultat de la Simulation de Résolution
- **Modèle testé :** `qwen2.5-7b`
- **Découverte du contrat :** `SUCCESS`
- **Chemin du contrat :** `runtime/hardware/trust/models/contracts/qwen2.5-7b.contract.json`
- **Statut global simulé :** `ALLOW`

## 2. Détail des Contrôles
### Contrôle : `trust_status`
  - status : `TRUSTED`
  - origin_verified : `True`
  - passed : `True`
### Contrôle : `resource_constraints`
  - contract_max_ram_mb : `8192`
  - contract_max_workers : `8`
  - ram_passed : `True`
  - workers_passed : `True`
  - passed : `True`
### Contrôle : `signature_integrity`
  - signature_present : `True`
  - signature_length : `64`
  - passed : `True`

## 3. Recherche des Implémentations HMAC / Secret dans le Dépôt
**Nombre de fichiers mentionnant HMAC ou Secret :** 57

- `discord_agent_v2.py`
- `web_server.py`
- `core/cloud_brain_broker.py`
- `core/cloud_connectors.py`
- `core/cloud_guard.py`
- `core/gemini_pro_provider.py`
- `core/knowledge_connectors.py`
- `core/omnipresence.py`
- `core/omni_brain.py`
- `interfaces/api/server.py`