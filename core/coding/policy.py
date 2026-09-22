"""E-ZZIO Core — Coding Policy.

Gouvernance locale : valide une ``CodingRequest`` avant exécution.

Capturé depuis ``core/cognition/antigravity/policy.py`` (2026-09-22)
avant décommissionnement.

**Objectif** : préserver les garde-fous (whitelist, modes sûrs) pour
que ``coder_worker`` ne puisse pas faire n'importe quoi.
"""
from __future__ import annotations

import logging
from pathlib import Path

from core.coding.protocol import (
    CodingPolicyViolationError,
    CodingRequest,
    ExecutionMode,
)

logger = logging.getLogger(__name__)


class CodingPolicy:
    """Gouvernance des requêtes de codage.

    Vérifie qu'une requête est conforme avant de la passer à ``CoderWorker``.

    Règles :
    1. Les fichiers touchés doivent être dans la whitelist (si définie).
    2. Les modes destructeurs (``ACCEPT_EDITS``) doivent être autorisés.
    3. La description ne doit pas être vide.
    4. Le chemin racine doit exister.
    """

    DEFAULT_ALLOWED_MODES: frozenset[ExecutionMode] = frozenset([
        ExecutionMode.READ_ONLY_SANDBOX,
        ExecutionMode.DRY_RUN,
    ])

    def __init__(
        self,
        root_dir: Path | str = ".",
        allowed_modes: frozenset[ExecutionMode] | None = None,
        whitelist_paths: set[str] | None = None,
    ) -> None:
        self.root_dir = Path(root_dir).resolve()
        self.allowed_modes = allowed_modes or self.DEFAULT_ALLOWED_MODES
        self.whitelist_paths = whitelist_paths

    def evaluate_request(self, request: CodingRequest) -> None:
        """Valide la requête. Lève ``CodingPolicyViolationError`` si invalide."""
        if not request.task_description.strip():
            raise CodingPolicyViolationError("task_description est vide")

        if request.mode not in self.allowed_modes:
            raise CodingPolicyViolationError(
                f"Mode '{request.mode}' non autorisé "
                f"(autorisés : {sorted(m.value for m in self.allowed_modes)})"
            )

        if not self.root_dir.exists():
            raise CodingPolicyViolationError(f"root_dir inexistant : {self.root_dir}")

        if self.whitelist_paths is not None:
            for f in request.files_context:
                if f not in self.whitelist_paths:
                    raise CodingPolicyViolationError(
                        f"Fichier hors whitelist : {f}"
                    )

        logger.debug("CodingRequest validée (mode=%s, effort=%s)", request.mode, request.effort)


__all__ = ["CodingPolicy"]
