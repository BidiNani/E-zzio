# E-ZZIO V7.11.0.4 — Dependency & Isolation Report

## 1. Violations d'Isolation de Domaine
- 🔴 `core\memory_core.py` : `core` -> `runtime`
- 🔴 `runtime\kernel_legacy_v2.py` : `runtime` -> `core`
- 🔴 `runtime\agent\controller.py` : `runtime` -> `core`
- 🔴 `runtime\agent\executor.py` : `runtime` -> `core`
- 🔴 `runtime\cognition\__init__.py` : `runtime` -> `core`
- 🔴 `runtime\core\context.py` : `core` -> `runtime`
- 🔴 `runtime\core\context.py` : `core` -> `runtime`
- 🔴 `runtime\core\ezzio_core.py` : `core` -> `runtime`
- 🔴 `runtime\core\ezzio_core.py` : `core` -> `runtime`
- 🔴 `runtime\core\ezzio_core.py` : `core` -> `runtime`
- 🔴 `runtime\core\ezzio_core.py` : `core` -> `runtime`
- 🔴 `runtime\gateway\adapter.py` : `runtime` -> `core`
- 🔴 `runtime\guardian\test_v615_3_models.py` : `runtime` -> `governance`
- 🔴 `runtime\guardian\test_v615_3_models.py` : `runtime` -> `governance`
- 🔴 `runtime\hardware\trust\execution\admission\controller.py` : `runtime` -> `governance`
- 🔴 `runtime\hardware\trust\models_governance\budget.py` : `runtime` -> `governance`
- 🔴 `runtime\memory\session.py` : `runtime` -> `core`
- 🔴 `runtime\memory\cortex\episodic.py` : `runtime` -> `core`
- 🔴 `runtime\memory\dream\engine.py` : `runtime` -> `core`
- 🔴 `runtime\memory\reflection\store.py` : `runtime` -> `core`
- 🔴 `runtime\memory\reflection\validator.py` : `runtime` -> `core`
- 🔴 `runtime\memory\semantic\contracts.py` : `runtime` -> `core`
- 🔴 `runtime\memory\sleep\scheduler.py` : `runtime` -> `core`

## 2. Graphe de dépendances (DOMAINS)

- `core` appelle -> `['core', 'runtime']`
- `runtime` appelle -> `['governance', 'core', 'runtime', 'sandbox']`
- `governance` appelle -> `['governance', 'runtime']`