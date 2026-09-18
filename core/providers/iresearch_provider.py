from abc import ABC, abstractmethod
from typing import Any


class IResearchProvider(ABC):
    @abstractmethod
    async def search(self, query: str, **kwargs: Any) -> dict[str, Any]:
        """Exécute une recherche asynchrone et retourne un dictionnaire normalisé."""
        pass
