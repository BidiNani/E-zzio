# E-ZZIO CANONICAL REPOSITORY MANIFEST & GOVERNANCE

## 1. BASELINE DE RÉFÉRENCE & INVENTAIRE
- **REPOSITORY ROOT**: `G:\AI\E-zzio`
- **BASELINE TAG**: `v10.6-certified`
- **BASELINE COMMIT**: `83c00af40fa8666c19cddf0fc1305c8e443b08e6`
- **REPOSITORY TYPE**: `D — HYBRID` (Mélange de projet canonique source, historique de benchmarks et runtime local)
- **TRACKED COUNT**: 4,830
- **UNTRACKED COUNT**: 22,699
- **PHYSICAL COUNT**: 27,529

---

## 2. REPOSITORY CLASSIFICATIONS & GOVERNANCE RULES

| Classification | Définition & Périmètre | Règle de Conservation |
| :--- | :--- | :--- |
| **CANONICAL_PROJECT** | Code source certifié, tests, outillage et documentation système (`core/`, `tests/`, `tools/`, `docs/`, `src/`). | Versionné. Toujours conservé. |
| **USER_DATA** | Scripts, configurations, agents et artifacts créés par l'utilisateur. | Protégé. Ne jamais supprimer automatiquement. |
| **RUNTIME_DATA** | États d'exécution locaux, files d'attente et working states (`runtime/`, `active/`). | Données locales. Conserver sans suppression automatique. |
| **AUDIT** | Rapports d'audit, preuves d'exécution et historiques de qualification (`state/audit/`, `state/evidence/`). | Protégé. Toujours conservé. |
| **CERTIFICATION** | Reçus officiels de scellement et certificats Git. | Protégé. Toujours conservé. |
| **GENERATED** | Artefacts générés par des pipelines déterministes. | Protégé sauf politique explicite de nettoyage. |
| **CACHE** | Caches temporaires d'exécution. | Conserver sous V10.6.2 (aucun nettoyage automatique). |
| **HISTORICAL** | Traces historiques d'expérimentation et anciens benchmarks. | Protégé. Ne pas supprimer. |
| **LEGACY** | Composants historiques remplacés par les évolutions V10.x. | Protégé. Conserver sans suppression (LEGACY != DELETE). |
| **PROTECTED** | Données sensibles, configurations d'intégration, état local. | Protégé. Toujours conservé. |
| **UNKNOWN** | Tout fichier ou dossier non formellement catégorisé. | **UNKNOWN = PROTECTED**. Règle Zéro de sécurité. |

---

## 3. RÈGLE D'OR DE GOUVERNANCE
> **UNKNOWN = PROTECTED**  
> Aucun fichier ne doit être supprimé, déplacé ou renommé sans preuve explicite et vérifiable.  
> La préservation des données et configurations utilisateur prévaut sur toute opération de nettoyage.
