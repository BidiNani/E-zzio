from abc import ABC, abstractmethod
from typing import List, Dict, Any
from runtime.recovery.contracts import Finding


class BaseAnalyzer(ABC):
    @abstractmethod
    def analyze(self, context: Dict[str, Any]) -> List[Finding]:
        pass
