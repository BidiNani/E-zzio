# E-ZZIO V7.8 — Matrice de l'Autorité de Signature & Normalisation
**Date :** 2026-08-11T15:57:55.126187

## Analyse Comparative des Primitives Cryptographiques

### Module : `runtime/hardware/trust/models/contract_signer.py`
- **Utilise HMAC (`hmac.new`) :** `True`
- **Utilise SHA256 (`hashlib.sha256`) :** `True`
- **Indices de hachage par concaténation (Secret + Payload) :** `True`
- **Sources de clés identifiées :** `['FILE / PATH']`
- **Extraits de code pertinents :**
  - `def __init__(self, secret_seed: str = "EZZIO_CORE_ROOT_KEY"):`
  - `self.secret_seed = secret_seed`
  - `def sign_file(self, file_path: Path):`
  - `# Calcul du HMAC-SHA256 (via hash avec secret)`
  - `signature = hashlib.sha256(encoded + self.secret_seed.encode("utf-8")).hexdigest()`

### Module : `runtime/hardware/trust/models/registry.py`
- **Utilise HMAC (`hmac.new`) :** `False`
- **Utilise SHA256 (`hashlib.sha256`) :** `True`
- **Indices de hachage par concaténation (Secret + Payload) :** `True`
- **Sources de clés identifiées :** `['FILE / PATH']`
- **Extraits de code pertinents :**
  - `def __init__(self, contract_dir: Path, secret_seed: str = "EZZIO_CORE_ROOT_KEY"):`
  - `self.secret_seed = secret_seed`
  - `expected = hashlib.sha256(encoded + self.secret_seed.encode("utf-8")).hexdigest()`

### Module : `runtime/hardware/trust/execution/attestation/verifier.py`
- **Utilise HMAC (`hmac.new`) :** `False`
- **Utilise SHA256 (`hashlib.sha256`) :** `True`
- **Indices de hachage par concaténation (Secret + Payload) :** `False`
- **Sources de clés identifiées :** `['FILE / PATH']`
- **Extraits de code pertinents :**
  - `def __init__(self, ledger: HashChainedLedger, secret_seed: str = "EZZIO_ATTESTOR_ROOT_KEY"):`
  - `self.secret_seed = secret_seed`
  - `contract_hash = hashlib.sha256(json.dumps(contract_details, sort_keys=True).encode("utf-8")).hexdigest()`
  - `h = hashlib.sha256()`
  - `h.update(self.secret_seed.encode("utf-8"))`
  - `return h.hexdigest()`
  - `def verify_receipt_signature(receipt: dict, secret_seed: str = "EZZIO_ATTESTOR_ROOT_KEY") -> bool:`
  - `h = hashlib.sha256()`
  - `h.update(secret_seed.encode("utf-8"))`
  - `expected_sig = h.hexdigest()`

### Module : `runtime/contracts/capability.py`
- **Utilise HMAC (`hmac.new`) :** `True`
- **Utilise SHA256 (`hashlib.sha256`) :** `True`
- **Indices de hachage par concaténation (Secret + Payload) :** `False`
- **Sources de clés identifiées :** `['FILE / PATH']`
- **Extraits de code pertinents :**
  - `import hmac`
  - `def __init__(self, secret: str = "ezzio-secret"):`
  - `if isinstance(secret, str):`
  - `self.secret = secret.encode("utf-8")`
  - `self.secret = secret or b"ezzio-secret"`
  - `def sign(token: Any, secret: Any = "ezzio-secret") -> str:`
  - `if isinstance(secret, str):`
  - `active_secret = secret.encode("utf-8")`
  - `active_secret = secret or b"ezzio-secret"`
  - `return hmac.new(`


## Recommandation de Normalisation (V7.8)
Pour garantir une interopérabilité parfaite entre l'émetteur (`contract_signer.py`) et le vérificateur (`models/registry.py`), la primitive cryptographique doit être unifiée sous un standard unique : **HMAC-SHA256** standardisé, éliminant toute construction par concaténation brute.