from abc import ABC, abstractmethod
from typing import List, Dict, Any

class BaseAnalyzer(ABC):
    @abstractmethod
    def analyze(self, context: Dict[str, Any]) -> List[str]:
        pass
