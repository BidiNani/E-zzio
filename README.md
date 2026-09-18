# E-ZZIO - Backend

Backend Python (FastAPI) du projet E-ZZIO.

## Prérequis

- Python 3.12 (via py launcher)
- PowerShell 7+
- Venv dans G:\AI\E-zzio\.venv

## Setup

    cd G:\AI\E-zzio
    pyi                              # helper PowerShell
    pip install -r requirements.txt
    pytest tests/ -q --tb=short

## Structure

- core/         Code metier (Frozen Core protege)
- routers/      Routes FastAPI
- tests/        Suite pytest
- docs/         Documentation + manifest Frozen Core
- web_server.py Point d'entree
- watchdog.ps1  Watchdog PowerShell

## Frozen Core

    python -m core.frozen_core.manifest          # verifier
    python -m core.frozen_core.manifest regen    # regenerer

## Hooks Git

.githooks/ via core.hooksPath. pre-commit + commit-msg.

## Dette technique

- Tests E2E Web UI desactives (Brave 153+ crashe sur Windows)
- web_server.py a decouper
