# E-ZZIO — Carte du chemin de démarrage

Analyse AST des imports locaux statiques depuis les entrypoints actifs.

## Entrypoints

- `web_server.py`
- `routers/master.py`
- `core/ezzio_master.py`
- `core/dispatcher.py`
- `core/llm_engine.py`

## Modules locaux atteignables (18)

- `core/__init__.py`
- `core/constitution/hardware_resource_governor.py`
- `core/dispatcher.py`
- `core/ezzio_master.py`
- `core/governor.py`
- `core/llm_engine.py`
- `core/memory.py`
- `core/memory_vault.py`
- `core/model_registry.py`
- `core/runtime/log_rotator.py`
- `core/storage.py`
- `core/telemetry.py`
- `routers/master.py`
- `runtime/execution/worker_bootstrap.py`
- `runtime/model_router/__init__.py`
- `runtime/routers/llm.py`
- `runtime/routers/mobile.py`
- `web_server.py`

## Arêtes d'import locales (19)

- `core/dispatcher.py` → `core.governor` → `core/governor.py`
- `core/dispatcher.py` → `core.llm_engine` → `core/llm_engine.py`
- `core/dispatcher.py` → `core.memory` → `core/memory.py`
- `core/dispatcher.py` → `core.model_registry` → `core/model_registry.py`
- `core/dispatcher.py` → `core.telemetry` → `core/telemetry.py`
- `core/ezzio_master.py` → `core` → `core/__init__.py`
- `core/ezzio_master.py` → `core.dispatcher` → `core/dispatcher.py`
- `core/ezzio_master.py` → `core.memory` → `core/memory.py`
- `core/ezzio_master.py` → `core.memory_vault` → `core/memory_vault.py`
- `core/memory_vault.py` → `core.storage` → `core/storage.py`
- `routers/master.py` → `core.ezzio_master` → `core/ezzio_master.py`
- `runtime/execution/worker_bootstrap.py` → `core.constitution.hardware_resource_governor` → `core/constitution/hardware_resource_governor.py`
- `runtime/routers/llm.py` → `runtime.model_router` → `runtime/model_router/__init__.py`
- `runtime/routers/mobile.py` → `runtime.model_router` → `runtime/model_router/__init__.py`
- `web_server.py` → `core.runtime.log_rotator` → `core/runtime/log_rotator.py`
- `web_server.py` → `routers.master` → `routers/master.py`
- `web_server.py` → `runtime.execution.worker_bootstrap` → `runtime/execution/worker_bootstrap.py`
- `web_server.py` → `runtime.routers.llm` → `runtime/routers/llm.py`
- `web_server.py` → `runtime.routers.mobile` → `runtime/routers/mobile.py`

## Erreurs / limites

- Aucune erreur de parsing dans les modules analysés.