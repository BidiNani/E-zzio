"""
E-ZZIO Core — Tactical Model Router (ECOL V7.61)
Sélectionne le moteur cognitif en fonction du vecteur de coût et de la capacité requise.
"""

import logging
from typing import Dict
from core.routing.model_registry import canonical_model_registry

logger = logging.getLogger(__name__)


class ModelRouter:
    def __init__(self):
        pass

    def select_engine(
        self,
        task_type: str = "general",
        complexity_score: float = 0.5,
        risk_level: str = "low",
        channel: str = "web",
        is_mission: bool = False,
        **kwargs
    ) -> Dict[str, str]:
        """Aiguillage capacitaire et conversationnel basé sur le registre canonique."""
        task_lower = (task_type or "").lower()

        # Specific specialized tasks
        if "code" in task_lower or "coding" in task_lower or "architecture" in task_lower:
            role = "CODING"
            thinking = "low"
        elif "forensic" in task_lower:
            role = "FORENSIC"
            thinking = "medium"
        elif "refactor" in task_lower:
            role = "REFACTOR"
            thinking = "medium"
        elif "infra" in task_lower or "fast_local" in task_lower:
            role = "FAST"
            thinking = "off"
        # Chat / Conversational & Strategic Missions
        elif complexity_score < 0.3 and risk_level == "low":
            role = "FAST_CHAT"
            thinking = "off"
        elif complexity_score < 0.7 and not (is_mission and complexity_score >= 0.7):
            role = "STANDARD_CHAT"
            thinking = "medium" if complexity_score >= 0.5 else "low"
        elif complexity_score >= 0.85:
            role = "MASTER_STRATEGIC"
            thinking = "high"
        else:
            role = "MASTER_STRATEGIC"
            thinking = "medium"

        # Lookup in canonical registry by role
        record = canonical_model_registry.get_by_role(role)

        # Fallback to MASTER if role not registered
        if not record:
            record = canonical_model_registry.get_by_role("MASTER_STRATEGIC") or canonical_model_registry.get_by_role("MASTER")

        engine = record.name if record else "gemini-3.8-flash"
        provider = "ollama" if record and record.source.name == "LOCAL" else "api"

        logger.info(
            f"Routage cognitif -> Canal: {channel} | Rôle: {role} | Moteur: {engine} | Thinking: {thinking} | Provider: {provider}"
        )
        return {"provider": provider, "model": engine, "thinking_level": thinking, "role": role}
