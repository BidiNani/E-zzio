"""
E-ZZIO Core — Tactical Model Router (ECOL V7.61)
Sélectionne le moteur cognitif en fonction du vecteur de coût et de la capacité requise.
"""

import logging
from typing import Dict

logger = logging.getLogger(__name__)


class ModelRouter:
    def __init__(self):
        self.local_fast = "qwen2.5:3b"
        self.local_coder = "qwen2.5-coder:7b"
        self.cloud_complex = "gemini-3.7-flash"

    def select_engine(self, task_type: str, complexity_score: float, risk_level: str) -> Dict[str, str]:
        """Aiguillage capacitaire strict."""
        if complexity_score < 0.3 and risk_level == "low":
            engine = self.local_fast
            provider = "ollama"
        elif "code" in task_type or "architecture" in task_type:
            engine = self.local_coder
            provider = "ollama"
        else:
            engine = self.cloud_complex
            provider = "api"

        logger.info(f"Routage cognitif -> Fournisseur: {provider} | Moteur: {engine}")
        return {"provider": provider, "model": engine}
