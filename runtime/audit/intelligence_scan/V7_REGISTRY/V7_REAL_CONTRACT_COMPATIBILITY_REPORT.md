# E-ZZIO V7.9.1 — Rapport de Test de Compatibilité Réelle des Contrats
**Date :** 2026-08-11T16:01:16.070743

## 1. Métadonnées du Contrat Réel
- **Fichier analysé :** `runtime/hardware/trust/models/contracts/qwen2.5-7b.contract.json`
- **Model ID :** `qwen2.5-7b`
- **Provider :** `{'execution_type': 'LOCAL', 'name': 'ollama'}`
- **Signature présente :** `True`
- **Valeur de signature :** `8376e7b8ad74e8b6f80fc086d6ca59b583c31c81ea68bf90c5e6f4bb007fac9c`

## 2. Analyse de l'Implémentation de `contract_signer.py`
- **Indices de sérialisation :** `['import json', 'data = json.load(f)', 'encoded = json.dumps(payload, sort_keys=True).encode("utf-8")', 'signature = hashlib.sha256(encoded + self.secret_seed.encode("utf-8")).hexdigest()', 'json.dump(data, f, indent=4, sort_keys=True)', 'print("Usage: python contract_signer.py <file.contract.json>")']`
- **Indices de clé :** `['def __init__(self, secret_seed: str = "EZZIO_CORE_ROOT_KEY"):', 'self.secret_seed = secret_seed', 'encoded = json.dumps(payload, sort_keys=True).encode("utf-8")', '# Calcul du HMAC-SHA256 (via hash avec secret)', 'signature = hashlib.sha256(encoded + self.secret_seed.encode("utf-8")).hexdigest()', 'json.dump(data, f, indent=4, sort_keys=True)']`

## 3. Résultats du Test de Compatibilité & Reproduction
- **LEGACY_SIGNATURE_REPRODUCED :** `False`
- **Détails du match :** `Aucune combinaison clé/sérialisation n'a permis de reproduire exactement la signature stockée dans le contrat.`

## 4. Conclusion de l'Étape V7.9.1
Ce test démontre si la signature actuelle du contrat peut être validée par une fonction de dérivation déterministe ou si une ré-émission des contrats sera nécessaire lors de la bascule vers l'autorité HMAC unifiée.