# E-ZZIO V7.0 — Architecture Consolidation Merge Plan

**Status:** PROPOSAL ONLY — NO AUTOMATIC MODIFICATION  
**Date:** 2026-08-11  
**Objective:** Eliminate architectural duplication while preserving runtime stability and core routing paths.

---

## 1. Model Registry & Contracts Consolidation

### Current State
- **Authority A (`core/model_registry.py`)**: Utilisé par le dispatcher, le superviseur et les routers. Gère les organes et les candidats de modèles rapides.
- **Authority B (`runtime/hardware/trust/models_governance/`)**: Utilisé par la V6.15.3 pour les budgets et les tokens d'admission.

### Target Authority
- **KEEP**: `core/model_registry.py` comme source unique de vérité (SSOT) pour l'identité et le catalogue des modèles.
- **ENHANCE**: Intégration des contrats déclaratifs signés HMAC (`*.contract.json`) directement lus par le registre unifié.

### Migration Actions
1. [ ] Étendre `core/model_registry.py` pour charger et vérifier la signature HMAC des contrats de `runtime/hardware/trust/models/contracts/`.
2. [ ] Faire pointer le `BudgetGovernor` de la trust layer vers cette API unifiée.
3. [ ] Marquer `runtime/hardware/trust/models_governance/` comme `DEPRECATED` et archiver le registre de test.

---

## 2. Governor Boundary Separation

### Current State
Plusieurs modules partagent le nom ou la logique de "Governor" (`core/governor.py`, `runtime/execution/governor.py`, `runtime/hardware/ryzen_optimizer/governor.py`).

### Target Authority
- **`core/governor.py`** : Supervision de haut niveau de la charge système et de l'état global.
- **`runtime/hardware/trust/execution/governor/`** : Enforcement strict des affinités CPU/RAM basées sur les grants d'admission (Zero-Trust).
- *Règle* : Pas de fusion de code entre la politique décisionnelle du Core et l'enforcement matériel de la Trust Layer.

---

## 3. Migration Safety Rules

- **Interdiction absolue** de suppression ou de renommage massif sans archivage préalable dans `runtime/archive/v7_migration/`.
- **Validation obligatoire** par le Guardian et les tests de non-régression après chaque patch de liaison.

---
