# E-ZZIO — Active Boot Boundary

## Statut

Cette frontière décrit les modules atteignables par import statique depuis le
backend FastAPI actif au moment de l'audit.

- Source de l'audit : `runtime/audit/boot_path_map.md`
- Entrypoint API : `web_server.py`
- Port local : `127.0.0.1:8001`
- Date de référence : 2026-08-15

## Entrypoints actifs

```text
web_server.py
routers/master.py
core/ezzio_master.py
core/dispatcher.py
core/llm_engine.py
```

## Chaîne de démarrage

```text
web_server.py
├── core/runtime/log_rotator.py
├── runtime/execution/worker_bootstrap.py
│   └── core/constitution/hardware_resource_governor.py
├── runtime/routers/llm.py
│   └── runtime/model_router/__init__.py
├── runtime/routers/mobile.py
│   └── runtime/model_router/__init__.py
└── routers/master.py
    └── core/ezzio_master.py
        ├── core/dispatcher.py
        │   ├── core/governor.py
        │   ├── core/llm_engine.py
        │   ├── core/memory.py
        │   ├── core/model_registry.py
        │   └── core/telemetry.py
        ├── core/memory.py
        └── core/memory_vault.py
            └── core/storage.py
```

## Modules Core actifs

```text
core/dispatcher.py
core/ezzio_master.py
core/governor.py
core/memory.py
core/model_registry.py
core/telemetry.py
core/tasks/manager.py
core/constitution/hardware_resource_governor.py
```

## Infrastructure active

```text
web_server.py
routers/master.py
core/llm_engine.py
core/memory_vault.py
core/storage.py
core/runtime/log_rotator.py
runtime/execution/worker_bootstrap.py
runtime/model_router/
runtime/routers/llm.py
runtime/routers/mobile.py
```

## Règle de migration

Aucun module actif ne doit être déplacé, supprimé ou renommé sans :

1. Une analyse de ses imports entrants.
2. Des tests de compilation et de comportement.
3. Une compatibilité temporaire si le chemin est utilisé ailleurs.
4. Un commit isolé et réversible.
5. Une mise à jour de cette frontière.

## Fichiers hors frontière

Tout fichier absent de cette carte n'est pas automatiquement inutile. Il est
simplement hors du chemin de démarrage statique actuel et doit être classé comme
`ACTIVE_LAZY`, `LEGACY`, `RUNTIME_DATA`, `ARCHIVE_CANDIDATE` ou `UNKNOWN`.
