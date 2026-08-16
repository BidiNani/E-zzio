# E-ZZIO V7 — Rapport d'Analyse des Dépendances Runtime & E/S Registre
**Date :** 2026-08-11T15:40:52.879450

## 1. Dépendances `core/` -> `runtime/`
**Nombre de modules Core important le Runtime :** 1

- `core/memory_core.py` :
  - importe `runtime.memory.sqlite.store`

## 2. Dépendances `runtime/` -> `core/` (Vérification des dépendances circulaires)
**Nombre de modules Runtime important le Core :** 17

- `runtime/kernel_legacy_v2.py` :
  - importe `runtime.core.message`
- `runtime/agent/controller.py` :
  - importe `runtime.core.microkernel`
- `runtime/agent/executor.py` :
  - importe `runtime.core.microkernel`
- `runtime/audit/microkernel_history/microkernel_after_2442.py` :
  - importe `runtime.core.events`
  - importe `runtime.core.version`
- `runtime/audit/microkernel_history/microkernel_after_final_cert.py` :
  - importe `runtime.core.events`
  - importe `runtime.core.version`
- `runtime/audit/microkernel_history/microkernel_before_2442.py` :
  - importe `runtime.core.events`
  - importe `runtime.core.version`
- `runtime/audit/microkernel_history/microkernel_before_certification.py` :
  - importe `runtime.core.events`
  - importe `runtime.core.version`
- `runtime/audit/microkernel_history/microkernel_before_final_cert.py` :
  - importe `runtime.core.events`
  - importe `runtime.core.version`
- `runtime/cognition/__init__.py` :
  - importe `runtime.cognition.core`
- `runtime/gateway/adapter.py` :
  - importe `runtime.core.ezzio_core`
- `runtime/memory/session.py` :
  - importe `runtime.core.message`
- `runtime/memory/cortex/episodic.py` :
  - importe `runtime.core.events`
- `runtime/memory/dream/engine.py` :
  - importe `runtime.core.events`
- `runtime/memory/reflection/store.py` :
  - importe `runtime.core.events`
- `runtime/memory/reflection/validator.py` :
  - importe `runtime.core.events`
- `runtime/memory/semantic/contracts.py` :
  - importe `core.memory_core`
- `runtime/memory/sleep/scheduler.py` :
  - importe `runtime.core.events`

## 3. Autopsie E/S de `core/model_registry.py`
Inspecte les fichiers réellement lus/ouverts par l'autorité de modèle centrale :
- **Fichiers / Chemins référencés :** ['G:/AI/E-zzio/registry/model_latency.json']
- **Appels de lecture (`open`/`read_text`) :** ['read_text']
- **Parsing JSON (`json.load`/`loads`) :** True
- **Recherche par motif (`glob`/`rglob`) :** []
