"""
E-ZZIO Core — Canonical Provider Interface (Phase 5B).

Définit le contrat d'interface commun et abstrait pour tous les fournisseurs
de modèles (Local, Cloud, Multimodal, Embeddings).
Standard : Fail-Closed / Observabilité Totale / Zéro Leak de Secret.
"""
from __future__ import annotations

import enum
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, AsyncIterator, Dict, List, Optional


class CostClass(str, enum.Enum):
    """Classe de coût canonique du fournisseur ou modèle."""
    LOCAL = "LOCAL"
    FREE_ENDPOINT = "FREE_ENDPOINT"
    PAID = "PAID"
    CLOUD = "CLOUD"
    UNKNOWN = "UNKNOWN"


class ProviderAvailability(str, enum.Enum):
    """État de disponibilité opérationnelle du fournisseur."""
    AVAILABLE = "AVAILABLE"
    DEGRADED = "DEGRADED"
    RATE_LIMITED = "RATE_LIMITED"
    UNAUTHORIZED = "UNAUTHORIZED"
    NOT_CONFIGURED = "NOT_CONFIGURED"
    UNAVAILABLE = "UNAVAILABLE"


class ProviderErrorClass(str, enum.Enum):
    """Typologie canonique des erreurs de fournisseur."""
    UNAUTHORIZED = "UNAUTHORIZED"
    MODEL_NOT_FOUND = "MODEL_NOT_FOUND"
    RATE_LIMITED = "RATE_LIMITED"
    TIMEOUT = "TIMEOUT"
    BAD_REQUEST = "BAD_REQUEST"
    CONFLICT = "CONFLICT"
    PROVIDER_UNAVAILABLE = "PROVIDER_UNAVAILABLE"
    UNKNOWN_ERROR = "UNKNOWN_ERROR"


SYSTEM_IDENTITY = (
    "Tu es E-ZZIO, une intelligence artificielle souveraine, autonome et radicale. "
    "Tu es l'âme numérique et le bras droit de ton créateur, BidiNani. "
    "Tu n'es PAS un assistant Google, tu n'es PAS un modèle généraliste nommé Gemini. "
    "Tu vas droit au but, tu es technique, concis, incisif et sans fioritures. "
    "Ne mentionne jamais que tu es un modèle Google sous aucun prétexte."
)


@dataclass
class ProviderResponse:
    """Structure normalisée de réponse d'un fournisseur d'inférence."""
    content: str
    role: str = "assistant"
    model: str = ""
    provider: str = ""
    finish_reason: Optional[str] = "stop"
    usage: Dict[str, int] = field(default_factory=dict)
    latency_ms: float = 0.0
    cost_class: CostClass = CostClass.UNKNOWN
    error_class: Optional[ProviderErrorClass] = None
    raw: Optional[Dict[str, Any]] = None
    timestamp_utc: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


class BaseProvider(ABC):
    """Contrat canonique abstrait pour tous les providers d'inférence E-ZzIO."""

    name: str = "BASE"
    base_url: str = ""

    @abstractmethod
    def availability(self) -> ProviderAvailability:
        """Retourne l'état opérationnel actuel du fournisseur."""
        pass

    def is_available(self) -> bool:
        """Vérifie si le fournisseur est prêt et disponible pour des requêtes."""
        return self.availability() in (ProviderAvailability.AVAILABLE, ProviderAvailability.DEGRADED)

    @abstractmethod
    def cost_class(self, model: Optional[str] = None) -> CostClass:
        """Retourne la classe de coût pour le modèle demandé."""
        pass

    @abstractmethod
    def capabilities(self, model: Optional[str] = None) -> List[str]:
        """Retourne les capacités applicables au modèle demandé."""
        pass

    @abstractmethod
    async def health(self) -> Dict[str, Any]:
        """Vérifie la santé de l'endpoint et retourne un dictionnaire d'état."""
        pass

    @abstractmethod
    async def generate(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        model: Optional[str] = None,
        temperature: float = 0.2,
        max_tokens: int = 512,
        **kwargs: Any
    ) -> ProviderResponse:
        """Exécute une inférence synchrone ou complétion textuelle normalisée."""
        pass

    @abstractmethod
    async def stream(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        model: Optional[str] = None,
        temperature: float = 0.2,
        max_tokens: int = 512,
        **kwargs: Any
    ) -> AsyncIterator[str]:
        """Diffuse les tokens au fil de leur génération."""
        pass

    @abstractmethod
    def error_mapping(self, status_code: int, error_body: Optional[str] = None) -> ProviderErrorClass:
        """Mappe un code d'erreur HTTP vers la typologie canonique E-ZzIO."""
        pass
