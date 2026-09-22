"""E-ZZIO Core — Coding Layer.

Protocole de codage inspiré d'Antigravity, sans dépendance externe.

Structure :
- ``protocol.py`` : CodingRequest, CodingResponse, ExecutionMode, EffortLevel
- ``policy.py``   : CodingPolicy (validation)
- ``bridge.py``   : InternalToolBridge (édition, git, shell)
- ``coder_worker.py`` : CoderWorker (boucle plan → build → verify)

Origine : capture du protocole ``core/cognition/antigravity/capabilities.py``
         le 2026-09-22, avant décommissionnement d'Antigravity.
"""
from __future__ import annotations

__all__ = [
    "protocol",
    "policy",
    "bridge",
    "coder_worker",
]
