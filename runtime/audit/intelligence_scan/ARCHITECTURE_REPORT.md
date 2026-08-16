# E-ZZIO V7.0 — Architecture & Intelligence Report
**Generated at:** 2026-08-11T13:18:25.335338Z
**Total files scanned:** 1155

## 1. Executive Summary
This report is the result of a read-only forensic scan across the entire E-ZZIO codebase.
No files were modified, moved, or deleted.

## 2. Authority Conflicts Detected
- **Domain:** Models & Registries
  - **Status:** CONफ्लικْت
  - **Resolution:** Merge into core/model_registry.py backed by signed *.contract.json
  - **Files:** core/model_registry.py, runtime/hardware/trust/models_governance/model_registry.py
- **Domain:** Resource Governance
  - **Status:** DISTRIBUTED_ROLES
  - **Resolution:** Keep separated by layer: Core Decision vs Trust Enforcement vs Ryzen Hardware vs Recovery
  - **Files:** core/governor.py, runtime/execution/governor.py, runtime/hardware/ryzen_optimizer/governor.py, runtime/recovery/decision/governor.py

## 3. Structural Duplicates (Non-Init)
Found 92 filename overlap groups.
- **persona.full.md** (3 instances): persona.full.md, registry/build/persona.full.md, runtime/identity/persona.full.md
- **readme.md** (2 instances): .pytest_cache/README.md, ezzio-ui/README.md
- **actions.py** (3 instances): core/actions.py, routers/actions.py, runtime/recovery/actions.py
- **autonomy.py** (2 instances): core/autonomy.py, routers/autonomy.py
- **ezzio_identity.py** (2 instances): core/ezzio_identity.py, routers/ezzio_identity.py
- **governor.py** (4 instances): core/governor.py, runtime/execution/governor.py, runtime/hardware/ryzen_optimizer/governor.py, runtime/recovery/decision/governor.py
- **human_chat.py** (2 instances): core/human_chat.py, routers/human_chat.py
- **human_loop.py** (2 instances): core/human_loop.py, routers/human_loop.py
- **memory.py** (2 instances): core/memory.py, routers/memory.py
- **model_registry.py** (2 instances): core/model_registry.py, runtime/hardware/trust/models_governance/model_registry.py
- **omnipresence.py** (2 instances): core/omnipresence.py, routers/omnipresence.py
- **pc_commander.py** (2 instances): core/pc_commander.py, routers/pc_commander.py
- **persona.py** (2 instances): core/persona.py, runtime/identity/persona.py
- **safe_actions.py** (2 instances): core/safe_actions.py, routers/safe_actions.py
- **supervisor.py** (4 instances): core/supervisor.py, routers/supervisor.py, runtime/execution/supervisor.py, runtime/external/supervisor.py