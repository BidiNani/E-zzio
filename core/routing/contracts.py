"""
E-ZZIO V7.24.2 — Routing Contracts
Définition des intentions, contraintes et décisions du routeur hybride.
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class Urgency(Enum):
    REALTIME = "realtime"  # ex: Chat Discord rapide
    NORMAL = "normal"  # ex: Tâche standard
    DEEP = "deep"  # ex: Analyse d'architecture, Refactoring


@dataclass
class RouteConstraints:
    urgency: Urgency = Urgency.NORMAL
    max_latency_ms: int = 5000
    require_privacy: bool = False
    allow_cloud: bool = True
    require_vision: bool = False
    model_swap_allowed: bool = True
    swap_penalty: float = 0.15  # Pénalité déduite du score si le modèle local n'est pas en RAM
    ram_pressure_penalty: float = 0.10  # Pénalité si le chargement sature le Governor


@dataclass
class ExecutionDecision:
    execution_plane: str  # "local" ou "cloud"
    provider: str  # "ollama", "gemini", "groq"
    model: str
    confidence_score: float
    reason: str
    metadata: dict[str, Any] = field(default_factory=dict)
