# E-ZZIO V7.0 — Architecture Consolidation & Refactoring Plan

**Status:** PROPOSAL ONLY / CONTROLLED CONSOLIDATION  
**Date:** 2026-08-11  
**Target:** Eliminate architectural duplication while preserving operational stability.

---

## 1. Classification & Action Matrix

### **KEEP (Modules Actifs & Autorités Officielles)**
- core/ezzio_master.py (Orchestration centrale)
- core/dispatcher.py (Routage des organes)
- core/model_registry.py (Autorité unique des modèles)
- untime/hardware/trust/models/contracts/*.contract.json (Vérité déclarative signée HMAC)
- untime/hardware/trust/execution/ (Admission, Governor, Attestation, Ledger)

### **MERGE (Fusion Contrôlée)**
- untime/hardware/trust/models_governance/model_registry.py $\rightarrow$ Fusionné et absorbé par core/model_registry.py + contracts/*.contract.json.
- Doublons de configuration de politiques $\rightarrow$ Unification sous le contrat de modèle et la politique de trust active.

### **ARCHIVE (Isolation & Rétention Historique)**
- Anciens prototypes de registres, scripts d'essais obsolètes et anciennes versions de test non référencées.
- Destination : untime/archive/v7_migration/ (avec journalisation dans migration_history.json).

---

## 2. Validation & Certification Requirements
La transition vers E-ZZIO V7.0 ne sera validée qu'après :
1. [ ] Intégrité de la chaîne de hachage du ledger vérifiée.
2. [ ] Résolution de modèles pilotée à 100% par les contrats signés HMAC.
3. [ ] Exécution réussie de la suite complète des tests de non-régression et de chaos.
4. [ ] Validation par le Guardian.
