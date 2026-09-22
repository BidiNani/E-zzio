"""E-ZZIO Core — Coding Protocol.

Protocole d'entrée/sortie pour les requêtes de codage.

Capturé depuis ``core/cognition/antigravity/capabilities.py`` (2026-09-22)
avant décommissionnement du bridge externe.

**Objectif** : préserver l'interface (noms de modes, efforts, formats)
pour que ``coder_worker`` puisse la reprendre à son compte.

Aucune dépendance externe. Aucun appel réseau.
"""
from __future__ import annotations

import enum
from dataclasses import dataclass, field
from typing import Any


class ExecutionMode(enum.StrEnum):
    """Mode d'exécution d'une tâche de codage.

    Inspiré d'Antigravity : ``READ_ONLY_SANDBOX`` et ``ACCEPT_EDITS``.

    - ``READ_ONLY_SANDBOX`` : le worker observe, analyse, propose — sans modifier.
    - ``ACCEPT_EDITS``     : le worker peut modifier les fichiers.
    - ``DRY_RUN``          : simulation complète sans écriture disque.
    """

    READ_ONLY_SANDBOX = "read_only_sandbox"
    ACCEPT_EDITS = "accept_edits"
    DRY_RUN = "dry_run"


class EffortLevel(enum.StrEnum):
    """Niveau d'effort alloué à la tâche.

    Inspiré d'Antigravity : ``HIGH`` / ``NORMAL`` / etc.

    - ``LOW``    : tâche simple, réponse rapide.
    - ``NORMAL`` : tâche standard.
    - ``HIGH``   : tâche complexe, plus de temps et de tokens alloués.
    """

    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"


class OutputFormat(enum.StrEnum):
    """Format de sortie attendu.

    - ``TEXT``  : texte brut (par défaut)
    - ``JSON``  : JSON structuré (pour un appel programmatique)
    - ``PATCH`` : diff unifié (pour application directe)
    """

    TEXT = "text"
    JSON = "json"
    PATCH = "patch"


@dataclass
class CodingRequest:
    """Requête de codage (entrée).

    Inspirée d'``AntigravityAgentRequest``, mais indépendante.
    """

    task_description: str
    """Description textuelle de la tâche à réaliser."""

    mode: ExecutionMode = ExecutionMode.READ_ONLY_SANDBOX
    """Mode d'exécution (voir ``ExecutionMode``)."""

    effort: EffortLevel = EffortLevel.NORMAL
    """Niveau d'effort (voir ``EffortLevel``)."""

    output_format: OutputFormat = OutputFormat.TEXT
    """Format de sortie attendu (voir ``OutputFormat``)."""

    files_context: list[str] = field(default_factory=list)
    """Liste des fichiers à considérer (chemins relatifs à la racine)."""

    context_metadata: dict[str, Any] = field(default_factory=dict)
    """Métadonnées additionnelles (idée de traçabilité, tags, etc.)."""


@dataclass
class CodingResponse:
    """Réponse de codage (sortie).

    Inspirée d'``AntigravityAgentResponse``, mais indépendante.
    """

    success: bool
    """Indique si la tâche a réussi."""

    result: dict[str, Any] = field(default_factory=dict)
    """Contenu de la réponse (format dépend de ``output_format``)."""

    iterations: int = 0
    """Nombre d'itérations de la boucle plan → build → verify."""

    audit_id: str = ""
    """Identifiant de traçabilité (pour brancher audit_ledger)."""

    error: str = ""
    """Message d'erreur (vide si ``success=True``)."""


class CodingPolicyViolationError(Exception):
    """Erreur levée quand une requête viole la politique de codage."""


__all__ = [
    "ExecutionMode",
    "EffortLevel",
    "OutputFormat",
    "CodingRequest",
    "CodingResponse",
    "CodingPolicyViolationError",
]
