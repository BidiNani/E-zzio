# E-ZZIO V7.10.0 — Execution Trace & Caller Report
**Date :** 2026-08-11T16:18:50.102634

## 1. Analyse Interne de `contract_signer.py`
- **Méthodes identifiées :** `['__init__', 'sign_file']`
- **Indices de gestion des clés/secrets :**
  - `def __init__(self, secret_seed: str = "EZZIO_CORE_ROOT_KEY"):`
  - `self.secret_seed = secret_seed`
  - `encoded = json.dumps(payload, sort_keys=True).encode("utf-8")`
  - `# Calcul du HMAC-SHA256 (via hash avec secret)`
  - `signature = hashlib.sha256(encoded + self.secret_seed.encode("utf-8")).hexdigest()`
  - `json.dump(data, f, indent=4, sort_keys=True)`

## 2. Appelants (`Callers`) de ContractSigner dans le Dépôt
**Nombre de modules appelants identifiés :** 4

### Fichier : `runtime/audit/v7_contract_birth_trace.py`
  - `search_terms = ["qwen2.5-7b", "contract.json", "ContractSigner", "max_allowed_workers"]`

### Fichier : `runtime/audit/v7_contract_generation_trace.py`
  - `has_signer = "ContractSigner" in content or "contract" in content.lower()`
  - `"uses_signer": "ContractSigner" in content`
  - `lines.append(f"- `{w['file']}` (Utilise ContractSigner: `{w['uses_signer']}`)")`

### Fichier : `runtime/audit/v7_execution_trace.py`
  - `"""Recherche tous les fichiers qui instancient ContractSigner ou appellent .sign_file"""`
  - `if "ContractSigner" in content or "sign_file" in content:`
  - `matching_lines = [line.strip() for line in content.splitlines() if "ContractSigner" in line or "sign_file" in line]`
  - `"## 2. Appelants (`Callers`) de ContractSigner dans le Dépôt",`

### Fichier : `runtime/hardware/trust/models/contract_signer.py`
  - `class ContractSigner:`
  - `def sign_file(self, file_path: Path):`
  - `signer = ContractSigner()`
  - `signer.sign_file(Path(sys.argv[1]))`


## 3. Conclusion V7.10.0
L'identification des appelants et l'autopsie interne de `contract_signer.py` permettent de lever le voile sur la chaîne d'instanciation. La migration reste bloquée jusqu'à l'examen de ce rapport de traçage.