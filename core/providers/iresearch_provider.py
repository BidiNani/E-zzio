from abc import ABC, abstractmethod
from typing import Any, Dict

class IResearchProvider(ABC):
    @abstractmethod
    async def search(self, query: str, **kwargs: Any) -> Dict[str, Any]:
        """Exécute une recherche asynchrone et retourne un dictionnaire normalisé."""
        pass
