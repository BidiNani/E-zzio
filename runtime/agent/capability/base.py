from abc import ABC, abstractmethod
from typing import Dict, Any


class Capability(ABC):
    name: str = "base.capability"
    description: str = "Capacité abstraite de base"
    risk_level: str = "LOW"

    @abstractmethod
    def run(self, parameters: Dict[str, Any]) -> Dict[str, Any]:
        pass
