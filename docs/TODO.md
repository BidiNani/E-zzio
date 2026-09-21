# Chantiers E-ZZIO

> Source de verite des chantiers restants.

## Traite recemment (2026-09-21)

| Chantier | Commit | Statut |
|---|---|---|
| TODO `routers/self.py:30` -> NOTE | `291592f` | Verifie |
| Fichiers vides supprimes (2) | `205dc84` | Verifie |
| Stubs orphelins supprimes (3) | `cb93558` | Verifie |
| `.gitignore` complete | `922c17d` | Verifie |
| `permissions: contents: read` CI | `f13e9e0` | Verifie |
| `actions/checkout@v5` + `setup-python@v6` | `5c24c8e` | Verifie |

## A traiter

### 1. Dualite web_server.py / src/ezzio/api.py

**Statut** : incertitude non resolue.

**Contexte** :
- `web_server.py` (452 lignes) : point d'entree confirme
- `src/ezzio/api.py` : branchement inconnu

**Decision** : consolider ou documenter.

**Verifiable par** : `grep -r "from src.ezzio.api" --include="*.py"`.

### 2. Sept fichiers >500 lignes

| Lignes | Fichier |
|---|---|
| 810 | `core/models/router.py` |
| 643 | `core/observability/metrics.py` |
| 634 | `core/safe_actions.py` |
| 607 | `routers/office.py` |
| 566 | `core/perception/universal_reader.py` |
| 533 | `core/omni_brain.py` |
| 502 | `core/ezzio_master.py` |

**Statut** : non traite.

**Decision** : splitter un par un, ou accepter.

**Verifiable par** : `wc -l` sur chaque fichier.

### 3. Warning pytest non bloquant

**Statut** : intentionnel.

**Fichier** : `core/models/capability_registry_source.py:27`

**Verifiable par** : `pytest tests/ -W error 2>&1 | grep -i capability`.

## Regles de traitement

Chaque chantier selon `docs/METHOD.md` :

1. Lire avant d'ecrire
2. Un fichier par commit
3. Garde-fous obligatoires
4. Rapport honnete
5. Rollback disponible

Pas de bloc "maitre". Pas de wildcard. Pas de `git add -A`.
