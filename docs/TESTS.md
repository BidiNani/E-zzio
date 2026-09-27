# Tests E-ZZIO - Guide complet

## Vue d'ensemble

La suite compte **2 352 tests** collectes (mesure du 2026-09-27).

**Ne pas recopier ce nombre a la main dans d'autres documents.** Il derive a
chaque ajout de test, et la suite a annonce historiquement 13 valeurs
differentes (106, 117, 123, 172, 231, 262, 270, 308, 311, 773, 807, 879, 880)
alors que le compte reel etait deja bien superieur. Pour le re-mesurer :

```bash
python -m pytest tests/ --collect-only -q
```

## Categories

| Categorie | Selection |
|-----------|-----------|
| Actifs (defaut) | `-m "not visual and not hardware"` — applique par defaut dans `pytest.ini` |
| Visual | Deselectionne par defaut, requiert des artefacts PNG/video |
| Hardware | Deselectionne par defaut, requiert un device physique |
| Integration | Actif par defaut, requiert un serveur sur 127.0.0.1:8001 |

## Commandes principales

```bash
python -m pytest tests/           # Suite par defaut (hors visual/hardware)
python -m pytest tests/ -m ""     # Tous les tests, y compris visual et hardware
python -m pytest tests/ -v        # Verbeux
python -m pytest tests/ -k "auth" # Sous-ensemble par mot-cle
```

## Marqueurs disponibles

| Marqueur | Signification |
|----------|---------------|
| unit | Test isole, aucun service externe |
| integration | Necessite un serveur sur 127.0.0.1:8001 |
| e2e | Necessite le serveur web et/ou Chromium |
| slow | Test lent (>10s) |
| hardware | Necessite un device ou artefact physique |
| visual | Test de certification visuelle (PNG/video) |

## Configuration

Fichier : **`pytest.ini`**. C'est la source unique de verite.

`pyproject.toml` contenait une seconde section `[tool.pytest.ini_options]` avec
la meme configuration et une liste de marqueurs divergente. Elle a ete supprimee
le 2026-09-27 : pytest lit `pytest.ini` en priorite, donc la section du pyproject
etait du drift silencieux. Ne pas la reintroduire.

### `--basetemp` est obligatoire

`pytest.ini` impose `--basetemp=tmp_pytest`. Ce n'est pas optionnel.

Sans lui, pytest utilise les repertoires numerotes du TEMP systeme
(`%LOCALAPPDATA%\Temp\pytest-of-enrik\`) et y cree un lien symbolique
`pytest-current`. Le nettoyage de ce lien echoue en `PermissionError:
[WinError 5] Acces refuse` pendant `pytest_sessionfinish`.

Consequence observee : **tous les tests passent mais pytest sort en code 1**.
Un agent qui boucle sur ses tests voit un echec permanent et relance en boucle
sans fin, alors que la cause est un lien residuel et non une regression.

Si `pytest-current` finit par bloquer (`Acces refuse` a la suppression), il faut
une elevation pour le retirer : il est devenu fantome, ni lisible ni supprimable
en permissions utilisateur.

## Depannage

**Tests web UI echouent** : lancer `python web_server.py` dans un autre terminal.

**Tests Android echouent** : utiliser `-m ""` pour les executer, ou skip.

**`PermissionError: [WinError 5]` en fin de run** : voir `--basetemp` ci-dessus.

**Import `runtime.*` echoue** : module archive le 18/09/2026. Migrer vers
`EzzioMaster` / `CodingAgentHarness`.
