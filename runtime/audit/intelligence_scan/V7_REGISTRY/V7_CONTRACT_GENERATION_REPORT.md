# E-ZZIO V7.9.9 — Contract Generation Trace Report
**Date :** 2026-08-11T16:17:36.172508

## 1. Modules identifiés comme potentiels rédacteurs/générateurs de contrats
**Nombre de modules :** 4

- `runtime/hardware/trust/execution/attestation/verifier.py` (Utilise ContractSigner: `False`)
- `runtime/hardware/trust/models/contract_signer.py` (Utilise ContractSigner: `True`)
- `runtime/hardware/trust/models/registry.py` (Utilise ContractSigner: `False`)
- `runtime/guardian/test_v616_attestation.py` (Utilise ContractSigner: `False`)

## 2. Fichiers récents dans le sous-système Trust

- `runtime/hardware/trust/models/contracts/qwen2.5-7b.contract.json` (Modifié le : `2026-08-11T14:56:31.647431`)
- `runtime/hardware/trust/models/resolver.py` (Modifié le : `2026-08-11T14:55:35.295829`)
- `runtime/hardware/trust/models/contract_signer.py` (Modifié le : `2026-08-11T14:54:21.356875`)
- `runtime/hardware/trust/models/registry.py` (Modifié le : `2026-08-11T14:51:19.893661`)
- `runtime/hardware/trust/execution/ledger/execution_ledger.jsonl` (Modifié le : `2026-08-11T14:41:38.443745`)
- `runtime/hardware/trust/execution/attestation/verifier.py` (Modifié le : `2026-08-11T14:41:04.608855`)
- `runtime/hardware/trust/execution/ledger/hashchain.py` (Modifié le : `2026-08-11T14:40:06.401805`)
- `runtime/hardware/trust/execution/attestation/collector.py` (Modifié le : `2026-08-11T14:39:59.963504`)
- `runtime/hardware/trust/execution/attestation/models.py` (Modifié le : `2026-08-11T14:39:46.639945`)
- `runtime/hardware/trust/revocation/storage_model_test/consumed_tokens.json` (Modifié le : `2026-08-11T14:34:20.419986`)
- `runtime/hardware/trust/models_governance/model_trust_registry.json` (Modifié le : `2026-08-11T14:34:20.418056`)
- `runtime/hardware/trust/execution/admission/controller.py` (Modifié le : `2026-08-11T14:33:30.206282`)
- `runtime/hardware/trust/models_governance/budget.py` (Modifié le : `2026-08-11T14:33:17.502799`)
- `runtime/hardware/trust/models_governance/model_registry.py` (Modifié le : `2026-08-11T14:33:17.452748`)
- `runtime/hardware/trust/revocation/storage_gov_test/consumed_tokens.json` (Modifié le : `2026-08-11T14:25:37.987192`)

## 3. Conclusion V7.9.9
L'analyse des modules d'écriture permet de cibler précisément le code responsable de l'instanciation des contrats. Le système demeure en lecture seule.