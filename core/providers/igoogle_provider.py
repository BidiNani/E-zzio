from abc import ABC, abstractmethod
from typing import Any


class IGoogleProvider(ABC):
    @abstractmethod
    async def execute(self, **kwargs: Any) -> dict[str, Any]:
        """Exécute une opération Google et retourne un dictionnaire normalisé."""

