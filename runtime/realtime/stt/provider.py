from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Dict, Any
import numpy as np

@dataclass
class SttResult:
    text: str
    confidence: float
    duration_s: float
    latencies: Dict[str, float] = field(default_factory=dict)
    provenance: Dict[str, Any] = field(default_factory=dict)

class ISttProvider(ABC):
    @abstractmethod
    async def transcribe(self, audio: np.ndarray, sample_rate: int) -> SttResult:
        pass
