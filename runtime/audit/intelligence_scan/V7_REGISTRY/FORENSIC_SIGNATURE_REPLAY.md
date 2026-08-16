# E-ZZIO V7.9.2 — Rapport de Forensic Replay des Signatures
**Date :** 2026-08-11T16:07:48.061357

## 1. Données Cibles
- **Signature stockée dans le contrat :** `8376e7b8ad74e8b6f80fc086d6ca59b583c31c81ea68bf90c5e6f4bb007fac9c`
- **Fichier de signature analysé :** `contract_signer.py`
- **Fichier de registre analysé :** `registry.py`

## 2. Résultats des Tests de Replay
- **Statut :** `NO_MATCH`
  - **Message :** `Aucune combinaison n'a produit la signature stockée. La clé de signature originelle est probablement externe ou un sel système spécifique a été utilisé.`

## 3. Analyse du Code Source (`contract_signer.py`)
```python
import json
import hashlib
import sys
from pathlib import Path

class ContractSigner:
    def __init__(self, secret_seed: str = "EZZIO_CORE_ROOT_KEY"):
        self.secret_seed = secret_seed

    def sign_file(self, file_path: Path):
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)

        # Extraction du payload pour signature (tout sauf "signature")
        payload = {k: v for k, v in data.items() if k != "signature"}
        
        # Sérialisation déterministe
        encoded = json.dumps(payload, sort_keys=True).encode("utf-8")
        
        # Calcul du HMAC-SHA256 (via hash avec secret)
        signature = hashlib.sha256(encoded + self.secret_seed.encode("utf-8")).hexdigest()
        
        data["signature"] = signature
        
       
```

## 4. Conclusion Forensic
L'échec de la reproduction directe indique que la signature d'origine a été émise avec un contexte de clé ou un hachage intermédiaire spécifique qu'il convient d'isoler en lisant directement `contract_signer.py` avant toute migration.