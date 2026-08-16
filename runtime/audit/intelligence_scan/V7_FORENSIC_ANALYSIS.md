# E-ZZIO V7 — Rapport d'Analyse Structurelle Forensic
**Fichiers analysés :** 1167

## 1. Integrité & Doublons Stricts (Identiques par SHA256)
**Nombre de groupes de fichiers 100% identiques :** 12

- Hash `e3b0c44298fc...` (3 copies) :
  - `core/__init__.py`
  - `runtime/memory/journal/__init__.py`
  - `runtime/memory/snapshots/__init__.py`
- Hash `b0b288b630c5...` (6 copies) :
  - `recovery/certified_state/microkernel.py`
  - `runtime/audit/microkernel_history/microkernel_after_final_cert.py`
  - `runtime/audit/microkernel_history/microkernel_after_2442.py`
  - `runtime/audit/microkernel_history/microkernel_before_2442.py`
  - `runtime/audit/microkernel_history/microkernel_before_certification.py`
  - `runtime/audit/microkernel_history/microkernel_before_final_cert.py`
- Hash `6da2f38ac5a6...` (2 copies) :
  - `registry/build/persona.full.md`
  - `runtime/identity/persona.full.md`
- Hash `87b089137dc4...` (2 copies) :
  - `registry/personality/lore.md`
  - `runtime/identity/lore.md`
- Hash `d6b32e102647...` (5 copies) :
  - `runtime/__init__.py`
  - `runtime/core/__init__.py`
  - `runtime/security/__init__.py`
  - `runtime/tools/__init__.py`
  - `runtime/tools/executors/__init__.py`
- Hash `8287f810ea5d...` (15 copies) :
  - `runtime/agent/capability/__init__.py`
  - `runtime/agent/ledger/__init__.py`
  - `runtime/audit/microkernel_history/__init__.py`
  - `runtime/events/__init__.py`
  - `runtime/governance/__init__.py`
  - `runtime/governor/__init__.py`
  - `runtime/identity/__init__.py`
  - `runtime/incidents/__init__.py`
  - `runtime/kernel/__init__.py`
  - `runtime/learning/__init__.py`
  - `runtime/memory/semantic/__init__.py`
  - `runtime/optimization/__init__.py`
  - `runtime/recovery/executor/__init__.py`
  - `runtime/skills/__init__.py`
  - `runtime_temp_forensic/EZZIO_MEMORY_FORENSIC_20260809_222237/__init__.py`
- Hash `7eb70257593d...` (18 copies) :
  - `runtime/budget/__init__.py`
  - `runtime/context/__init__.py`
  - `runtime/external/__init__.py`
  - `runtime/external/platform/__init__.py`
  - `runtime/memory/affect/__init__.py`
  - `runtime/memory/cortex/__init__.py`
  - `runtime/memory/cortex/semantic/__init__.py`
  - `runtime/memory/dream/__init__.py`
  - `runtime/memory/reflection/__init__.py`
  - `runtime/memory/signals/__init__.py`
  - `runtime/memory/sleep/__init__.py`
  - `runtime/memory/sqlite/__init__.py`
  - `runtime/observability/__init__.py`
  - `runtime/policy/__init__.py`
  - `runtime/router/__init__.py`
  - `runtime/sensors/__init__.py`
  - `runtime/state/__init__.py`
  - `tests/__init__.py`
- Hash `f0a9bf478d39...` (2 copies) :
  - `runtime/external/base.py`
  - `runtime/tools/base.py`
- Hash `4ba4fbafbde9...` (2 copies) :
  - `runtime/memory/atomic_writer.py`
  - `runtime/test_isolation/v453/atomic_writer.py`
- Hash `84830ede31de...` (2 copies) :
  - `runtime/test_isolation/v540/sandbox_real_engine/manifest.json`
  - `runtime/test_isolation/v610/sandbox_e2e_real/manifest.json`

## 2. Modules Python Potentiellement Orphelins
**Nombre de modules sans dépendants entrants (hors scripts/entrypoints) :** 33

- `run_ezzio.py`
- `routers/actions.py`
- `routers/autonomy.py`
- `routers/brain.py`
- `routers/brain_gateway.py`
- `routers/chat.py`
- `routers/cloud.py`
- `routers/cloud_brain.py`
- `routers/ezzio_identity.py`
- `routers/ezzio_unified.py`
- `routers/forge.py`
- `routers/human_chat.py`
- `routers/human_loop.py`
- `routers/knowledge.py`
- `routers/memory.py`

## 3. Chaînes d'Exécution des Points d'Entrée Principaux

### Point d'Entrée : `core/ezzio_master.py`
- **Importé par :** 54 module(s)
- **Imports directs (7) :**
  - `core.safe_actions`
  - `core.memory.ezzio_memory`
  - `pathlib.Path`
  - `sys`
  - `core.dispatcher.ezzio_dispatcher`
  - `cloud_brain_broker`
  - `asyncio`

### Point d'Entrée : `web_server.py`
- **Importé par :** 0 module(s)
- **Imports directs (14) :**
  - `uvicorn`
  - `urllib.parse`
  - `time`
  - `asyncio`
  - `fastapi.FastAPI`
  - `typing.Optional`
  - `datetime.datetime`
  - `runtime.memory.semantic.contracts.memory_core`
  - `dotenv.load_dotenv`
  - `pydantic.BaseModel`

### Point d'Entrée : `core/pc_commander.py`
- **Importé par :** 43 module(s)
- **Imports directs (11) :**
  - `pathlib.Path`
  - `typing.Any`
  - `time`
  - `json`
  - `core.human_chat.human_chat`
  - `os`
  - `core.safe_actions.quick_action`
  - `__future__.annotations`
  - `core.safe_actions.cancel_proposal`
  - `core.safe_actions.propose_action`

### Point d'Entrée : `core/dispatcher.py`
- **Importé par :** 43 module(s)
- **Imports directs (5) :**
  - `core.llm_engine.query_model_async`
  - `core.governor.analyze_request`
  - `core.model_registry.ORGANS`
  - `core.telemetry.log_event`
  - `core.memory.ezzio_memory`
