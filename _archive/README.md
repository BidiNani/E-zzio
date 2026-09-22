# `_archive/` — Archives du projet E-zzio

> **Ce dossier contient 328 fichiers archivés, répartis en 11 sous-dossiers.**
> **Aucun de ces fichiers n'est utilisé par le code de production.**
>
> Index créé le **2026-09-22** pour documenter ce dossier.

---

## Règle de gouvernance

**Ajout dans `_archive/` sans :**
1. Raison explicite (code mort, version obsolète, test legacy…)
2. Référence Git (commit ou branche d'origine)
3. Ligne dans cet index
4. Date de révision

**Suppression de `_archive/` sans :**
1. Vérifier qu'aucun fichier n'est référencé (grep sur tout le dépôt)
2. Documenter la suppression dans la section « Historique »

---

## Index des sous-dossiers

| Dossier | Fichiers | Taille | Date | Révision |
|---|---|---|---|---|
| `core_evolution/` | 7 | 12,9 Ko | 2026-09-19 | 2027-03-19 |
| `docs_certified_20260922_112042/` | variable | variable | 2026-09-22 | 2027-03-22 |
| `docs_versions/` | 11 | 42,6 Ko | 2026-09-19 | 2027-03-19 |
| `legacy_cleanup_20260919_144613/` | 5 | 42,7 Ko | 2026-09-19 | 2027-03-19 |
| `legacy_tests_v17_v18_v19_20260919_151146/` | 23 | 20,7 Ko | 2026-09-19 | 2027-03-19 |
| `orphan_dirs_20260919_133105/` | 7 | 10,3 Ko | 2026-09-19 | 2027-03-19 |
| `orphans_confirmed_20260919_141926/` | 3 | 12,4 Ko | 2026-09-19 | 2027-03-19 |
| `ps_versions/` | 104 | 1178,1 Ko | 2026-09-19 | 2027-03-19 |
| `tools_ast_20260919_140348/` | 71 | 627,3 Ko | 2026-09-19 | 2027-03-19 |
| `tools_audit_20260919_135403/` | 50 | 144,2 Ko | 2026-09-19 | 2027-03-19 |
| `tools_safe_20260919_134823/` | 46 | 154,0 Ko | 2026-09-19 | 2027-03-19 |

**TOTAL : 328 fichiers, ~2,2 Mo.**

---

## Détail par sous-dossier

### `core_evolution/`
Versions antérieures de modules `core/` lors de refactorings.

### `docs_certified_20260922_112042/`
Rapports auto-certifiés V9.1 → V9.4 (statuts non reproductibles par un tiers).
**Note** : exempté du `.gitignore` (`!_archive/docs_certified_*/`).

### `docs_versions/`
Versions antérieures de documents `docs/`.

### `legacy_cleanup_20260919_144613/`
Nettoyage legacy du 2026-09-19.

### `legacy_tests_v17_v18_v19_20260919_151146/`
Tests des versions 17, 18, 19 du projet, obsolètes.

### `orphan_dirs_20260919_133105/`
Dossiers orphelins identifiés lors du nettoyage.

### `orphans_confirmed_20260919_141926/`
Fichiers confirmés orphelins après vérification.

### `ps_versions/`
Versions antérieures de scripts PowerShell.
**Note** : plus gros sous-dossier (104 fichiers, 52% du volume total).

### `tools_ast_20260919_140348/`
Snapshots d'analyse AST des outils `core/tools/`.

### `tools_audit_20260919_135403/`
Rapports d'audit des outils.

### `tools_safe_20260919_134823/`
Versions « safe » des outils lors du nettoyage.

---

## Politique de révision

**Tous les 6 mois** (prochaine : **2027-03-19** et **2027-03-22**), chaque sous-dossier est réévalué :

- **Si aucun fichier consulté** depuis l'archivage → candidat à suppression
- **Si des fichiers consultés** → prolonger de 6 mois
- **Toujours documenter** la décision

---

## Historique

- **2026-09-22** : création de cet index.
- **2026-09-22** : ajout de `docs_certified_20260922_112042/` (11 rapports auto-certifiés V9.1 → V9.4).