from abc import ABC, abstractmethod
from typing import Dict, Any


class BaseActionExecutor(ABC):
    @abstractmethod
    def execute(self, parameters: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        pass
