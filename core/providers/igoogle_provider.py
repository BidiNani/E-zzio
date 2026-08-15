from abc import ABC, abstractmethod
from typing import Any, Dict

class IGoogleProvider(ABC):
    @abstractmethod
    async def execute(self, **kwargs: Any) -> Dict[str, Any]:
        """Exécute une opération Google et retourne un dictionnaire normalisé."""
        pass
