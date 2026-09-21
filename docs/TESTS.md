# Tests E-ZZIO - Guide complet

## Vue d'ensemble

La suite compte **807 tests** repartis en 4 categories.

| Categorie | Nombre | Par defaut |
|-----------|--------|------------|
| Actifs | 773 | Executes |
| Skipped | 5 | Ignores |
| Visual | ~16 | Deselectionnes |
| Hardware | ~8 | Deselectionnes |


## Commandes principales

```bash
python -m pytest tests/           # Suite par defaut (773 tests, ~90s)
python -m pytest tests/ -m ""     # Tous les tests (y compris visual/hardware)
python -m pytest tests/ -v        # Verbeux
```

## Marqueurs disponibles

| Marqueur | Signification |
|----------|---------------|
| integration | Necessite un serveur sur 127.0.0.1:8001 |
| visual | Verifie des artefacts PNG/video |
| hardware | Necessite un device ou artefact |
| slow | Test lent (>10s) |


## Configuration

Fichier : pyproject.toml section [tool.pytest.ini_options]
Source unique de verite (pytest.ini supprime).


## Depannage

**Tests web UI echouent** : lancer python web_server.py dans un autre terminal.

**Tests Android echouent** : utiliser -m " pour les executer, ou skip.

**Import runtime.* echoue** : module archive le 18/09/2026. Migrer vers EzzioMaster / CodingAgentHarness.

