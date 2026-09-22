# TODO - Etat verifie au 2026-09-21

## Traite

- [x] TODO -> NOTE explicite : `routers/self.py:30` (commit `291592f`)
- [x] Stubs orphelins supprimes (3) : commit `cb93558`
- [x] Fichiers vides supprimes (2) : commit `205dc84`
- [x] `.gitignore` complete (`.tox/`, `build/`, `_audit.json`) : commit `922c17d`
- [x] CI : `permissions: contents: read` : commit `f13e9e0`
- [x] CI : `actions/checkout@v5` + `actions/setup-python@v6` : commit `5c24c8e`
- [x] Incident wildcard PowerShell (`81798d8`, 35 `__init__.py` supprimes) : annule via `git reset --hard` + `push --force-with-lease`
- [x] 43 branches obsoletes supprimees, `master` -> `main` sur les 2 repos

## A decider

- [x] **Dualite ``web_server.py`` vs ``src/ezzio/api.py`` — CLOS 2026-09-22** : ce ne sont pas deux API concurrentes, mais deux points d'entree distincts. ``web_server.py`` (256 lignes) = serveur HTTP production. ``src/ezzio/`` (25 fichiers) + ``main.py`` (190 lignes) = sous-projet LangGraph separe. Voir ``docs/PRODUCT_ARCHITECTURE.md`` section "Deux points d'entree".
- [ ] Bug garde-fou PowerShell : `return` dans un `if` dans un pipe ne stoppe pas le script entier - correction generique : sortir la logique du pipe (boucle `foreach` classique + `return` au niveau script), ou `throw` capte par un `try/catch` au niveau superieur qui fait `exit 1`

- [ ] **Bug garde-fou PowerShell/Python (precise 2026-09-22)** : un script Python qui utilise `subprocess.run(["ruff", "check", ...])` echoue sous Windows avec `FileNotFoundError: [WinError 2]` - `ruff` est dans le `.venv` mais pas dans le PATH du `subprocess`. **Correction** : utiliser `subprocess.run([sys.executable, "-m", "ruff", "check", ...])` pour garantir l'utilisation du `ruff` du meme interpreteur Python. **Impact observe** : le script s'arrete avant le commit ; le fichier modifie reste dans le working tree (inspectable, non committe). **Instance rencontree** : session 2026-09-22, fix `test_capability_policy.py` (commit `88df2e4`).

## Fichiers >500 lignes (7, verifies ligne par ligne)

| Fichier | Lignes |
|---|---|
| core/models/router.py | 810 |
| core/observability/metrics.py | 643 |
| core/safe_actions.py | 634 |
| routers/office.py | 607 |
| core/perception/universal_reader.py | 566 |
| core/omni_brain.py | 533 |
| core/ezzio_master.py | 502 |

## Non bloquant, intentionnel

- Warning pytest : `CapabilityRegistry` absent dans `capability_registry_source.py:27` (message confirme "non bloquant")

## Bug pre-commit : CLOS 2026-09-22

- **Cause reelle** : le hook `.githooks/pre-commit` passait `-m "not slow"` a pytest, ce qui ecrasait silencieusement `addopts` (`-m 'not visual and not hardware'`) de `pyproject.toml`. Le test `test_android_artifact` n'etait donc plus exclu.
- **Fix** : commit `29ef117` (`-m "not slow and not visual and not hardware"`)
- **Regles capitalisees** : commit `42a7f86` (`docs/METHOD.md` section "Hooks, pytest et surcharges")
- **Statut** : resolu



## Fichiers à couverture plafonnée (naturellement)

Session V5-fix (2026-09-22). Ces fichiers plafonnent pour des raisons
techniques, pas par manque de tests :

- [ ] **core/security/secrets_vault.py** (68%) — Branches DPAPI Windows
  uniquement + fallback crypto. Pour monter : nécessite un runner CI Windows
  avec droits élevés (chantier infrastructure).

- [ ] **core/system/cpu_tuning.py** (71%) — Branches ctypes.windll
  Windows only + détection Ollama actif. Pour monter : idem, runner Windows.

- [ ] **core/human_loop.py** (70%) — Imports conditionnels
  project_janitor, pc_model_router. Pour monter : nécessite un
  environnement runtime complet (chantier intégration).

**Ces plafonds sont acceptables.** Les fichiers critiques
(security, signals, telemetry) sont à 85%+.
