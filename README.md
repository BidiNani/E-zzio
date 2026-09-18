# E-ZZIO - Backend

Backend Python (FastAPI) du projet E-ZZIO.

## Prérequis

- **Python 3.12** (via `py` launcher Windows ou `python.org`)
- **PowerShell 7+** (pas Windows PowerShell 5.1)
- Un venv dans `G:\AI\E-zzio\.venv`

## Setup rapide

    cd G:\AI\E-zzio
    pyi                              # helper PowerShell (affiche .venv)
    pip install -r requirements.txt
    pytest tests/ -q --tb=short

## Structure

    core/         Code métier (Frozen Core protégé)
    routers/      Routes FastAPI découpées
    tests/        Suite pytest (879 tests, 4 skipped)
    docs/         Documentation + manifest Frozen Core
    web_server.py Point d'entrée FastAPI (452 lignes)
    watchdog.ps1  Watchdog PowerShell

## Routes principales

- `/health`, `/ping`     -> `routers/health.py` (source unique)
- `/metrics`               -> `routers/health.py` (uptime_s, circuit_breaker,
                               providers_health.ollama_local)
- `/perception/status`     -> `routers/perception.py`
- `/master/*`              -> `routers/master.py`
- `/memory/*`              -> `routers/memory.py`

## Frozen Core

Vérifie l'intégrité cryptographique des fichiers sensibles :

    python -m core.frozen_core.manifest          # vérifier
    python -m core.frozen_core.manifest regen    # régénérer

Manifest : `docs/FROZEN_CORE_MANIFEST.json`

## Hooks Git

`.githooks/` versionné, activé via `core.hooksPath`.
- `pre-commit` : lint + tests rapides
- `commit-msg` : anti-doublon

## Tests

    pytest tests/ -q --tb=short
    # 879 passed, 4 skipped, 23 warnings

## Dette technique

- Tests E2E Web UI désactivés (Brave 153+ crashe sur Windows).
- `test_v94_living_office_evidence` : à investiguer (Frozen Core drift).
- `web_server.py` (452 lignes) : pourrait descendre sous 200 lignes
  en découpant d'autres routes inline (/api/models*, /api/tools).

## Tailles actuelles

- web_server.py        : 452 lignes
- routers/health.py    : 28 lignes