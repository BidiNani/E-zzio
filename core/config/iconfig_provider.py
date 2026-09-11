from typing import Any, Dict, Optional
from abc import ABC, abstractmethod


class IConfigProvider(ABC):
    """Contrat d'interface pour les providers de configuration."""

    @abstractmethod
    async def get_config(self, key: str) -> Optional[Any]:
        """Récupère une valeur de configuration par clé."""
        pass

    @abstractmethod
    async def set_config(self, key: str, value: Any) -> None:
        """Définit une valeur de configuration."""
        pass

    @abstractmethod
    async def list_configs(self, prefix: str = "") -> Dict[str, Any]:
        """Liste toutes les configurations avec un préfixe donné."""
        pass
