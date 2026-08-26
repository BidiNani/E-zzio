"""E-ZZIO Intent-to-Fabric Integration Connector.

Bridges the cognitive intent pipeline with the Autonomous Model Fabric router.
"""

from __future__ import annotations

import re
import time
from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any

from core.models.fabric import AutonomousModelFabric, build_fabric
from core.models.registry import ModelTier
from core.models.errors import FabricError, ProviderExhaustedError


class IntentCategory(StrEnum):
    """Catégories fonctionnelles d'intentions reconnues par E-zzio."""
    FAST_DIALOGUE = "FAST_DIALOGUE"      # Salutations, questions simples, accusés de réception
    SYSTEM_COMMAND = "SYSTEM_COMMAND"    # Tâches de contrôle, diagnostic, micro-kernel status
    CODE_ANALYSIS = "CODE_ANALYSIS"      # Parsing AST, refactoring, génération de scripts
    DEEP_REASONING = "DEEP_REASONING"    # Résolution complexe, stratégie, synthèse multi-sources


INTENT_TIER_MAP: dict[IntentCategory, str] = {
    IntentCategory.FAST_DIALOGUE: ModelTier.FAST.value,
    IntentCategory.SYSTEM_COMMAND: ModelTier.FAST.value,
    IntentCategory.CODE_ANALYSIS: ModelTier.MID.value,
    IntentCategory.DEEP_REASONING: ModelTier.MID.value,
}


@dataclass(slots=True)
class IntentExecutionResult:
    """Résultat enrichi de l'exécution d'une intention via le Fabric."""
    intent: IntentCategory
    tier_requested: str
    content: str
    provider_used: str
    model_used: str
    slot_used: str
    execution_time_ms: float
    success: bool = True
    reasoning: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


class IntentFabricConnector:
    """Connecteur principal orchestrant l'exécution des intentions cognitives."""

    def __init__(self, fabric: AutonomousModelFabric | None = None, project_root: str = "G:\\AI\\E-zzio") -> None:
        self.fabric = fabric or build_fabric(project_root=project_root)

    def resolve_tier(self, intent: IntentCategory | str) -> str:
        """Détermine le palier requis pour une intention donnée."""
        if isinstance(intent, str):
            try:
                intent = IntentCategory(intent)
            except ValueError:
                return ModelTier.FAST.value
        return INTENT_TIER_MAP.get(intent, ModelTier.FAST.value)

    @staticmethod
    def _extract_reasoning(raw_content: str) -> tuple[str, str | None]:
        """Extrait et sépare les balises <think>...</think> de la réponse finale."""
        pattern = r"<think>(.*?)</think>"
        match = re.search(pattern, raw_content, flags=re.DOTALL)
        
        if match:
            reasoning = match.group(1).strip()
            clean_content = re.sub(pattern, "", raw_content, flags=re.DOTALL).strip()
            return clean_content, reasoning
        
        return raw_content.strip(), None

    async def execute_intent(
        self,
        *,
        intent: IntentCategory | str,
        messages: list[dict[str, str]],
        temperature: float = 0.2,
        max_tokens: int | None = None,
    ) -> IntentExecutionResult:
        """Achemine une intention vers le modèle qualifié actif approprié."""
        target_tier = self.resolve_tier(intent)
        start_time = time.perf_counter()

        try:
            response = await self.fabric.router.execute(
                messages=messages,
                tier=target_tier,
                temperature=temperature,
                max_tokens=max_tokens,
            )
            elapsed_ms = round((time.perf_counter() - start_time) * 1000.0, 2)
            
            raw_text = response.get("content", "")
            clean_text, reasoning_text = self._extract_reasoning(raw_text)

            return IntentExecutionResult(
                intent=IntentCategory(intent) if isinstance(intent, str) else intent,
                tier_requested=target_tier,
                content=clean_text,
                reasoning=reasoning_text,
                provider_used=response.get("provider", "unknown"),
                model_used=response.get("model", "unknown"),
                slot_used=response.get("slot", "unknown"),
                execution_time_ms=elapsed_ms,
                success=True,
            )

        except (ProviderExhaustedError, FabricError) as exc:
            elapsed_ms = round((time.perf_counter() - start_time) * 1000.0, 2)
            self.fabric.telemetry.emit(
                "intent_routing_failed",
                {
                    "intent": str(intent),
                    "tier": target_tier,
                    "error": str(exc),
                    "duration_ms": elapsed_ms,
                },
            )
            raise RuntimeError(f"Échec d'exécution de l'intention [{intent}] sur le palier [{target_tier}]: {exc}") from exc
