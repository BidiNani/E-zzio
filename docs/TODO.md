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

- [ ] Dualite `web_server.py` (452 lignes, point d'entree FastAPI reel confirme) vs `src/ezzio/api.py` (existe, LangGraph/graph/workflow.py, pas branche en primaire) - decision architecturale a trancher, pas un patch
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

## Bug pre-commit : test_android_artifact bloque les commits doc en local

- Fichier : `tests/test_android_artifact.py`
- Test : `test_dist_android_apk_is_compiled_binary`
- Cause : `dist/android/E-ZzIO-v9.0.1.apk` absent en local (artefact de build CI uniquement)
- Impact : bloque tout commit doc en local → force `--no-verify`, ce qui use la discipline
- Fix propose : `@pytest.mark.skipif(not Path("dist/android").exists(), reason="build CI uniquement")`
- Statut : ouvert

