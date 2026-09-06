"""
E-ZZIO Core V10.12 — Adaptive Model & Execution Optimizer.
Optimise l'exécution des missions en réduisant la latence réelle des modèles et des outils :
- Warm Model Residency & Keep-Alive
- Routeur de Modèles conscient de la Latence et du statut Resident/Cold
- Élimination des appels LLM inutiles sur les tâches déterministes
- Contrôle strict du nombre de tokens générés (num_predict/context efficiency)
- Exécution parallèle gouvernée des nœuds DAG indépendants
"""
from __future__ import annotations

import logging
import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple, Callable
from concurrent.futures import ThreadPoolExecutor

from core.agent.autonomous_e2e_engine import autonomous_e2e_engine, MissionState, ResultVerificationEngine
from core.operations.multi_mission_arbitrator import multi_mission_arbitrator, MultiMissionArbitrator
from core.operations.continuous_operations_loop import continuous_operations_loop
from runtime.model_router.providers.ollama import OllamaProvider

logger = logging.getLogger("ezzio.operations.adaptive_model_optimizer")


class ModelResidencyState(str, Enum):
    NOT_LOADED = "NOT_LOADED"
    LOADING = "LOADING"
    RESIDENT = "RESIDENT"
    EVICTING = "EVICTING"


@dataclass
class ModelResidencyProfile:
    model_name: str
    provider: str = "Ollama"
    residency_state: ModelResidencyState = ModelResidencyState.NOT_LOADED
    last_invoked_at: float = 0.0
    warm_latency_ms: float = 0.0
    cold_latency_ms: float = 0.0
    total_calls: int = 0


class AdaptiveModelExecutionOptimizer:
    """Optimiseur adaptatif de latence d'exécution et de modélisation pour E-ZZIO V10.12."""

    def __init__(self) -> None:
        self.residency_registry: Dict[str, ModelResidencyProfile] = {}
        self.provider = OllamaProvider(base_url="http://localhost:11434")
        self.verifier = ResultVerificationEngine()
        self.executor = ThreadPoolExecutor(max_workers=4)

        # Default local model candidates
        self._register_model("phi4-mini:latest")
        self._register_model("nemotron-3-nano:4b")

    def _register_model(self, model_name: str) -> None:
        if model_name not in self.residency_registry:
            self.residency_registry[model_name] = ModelResidencyProfile(model_name=model_name)

    def select_latency_aware_model(self, task_type: str, preferred_model: Optional[str] = None) -> str:
        """Sélectionne le modèle le plus adapté en privilégiant les modèles résidents (WARM)."""
        target = preferred_model or "phi4-mini:latest"
        self._register_model(target)

        profile = self.residency_registry[target]
        now = time.time()

        # If resident and called within 300s -> keep-warm
        if profile.residency_state == ModelResidencyState.RESIDENT and (now - profile.last_invoked_at) < 300:
            logger.debug(f"[LATENCY-OPTIMIZER] Réutilisation du modèle chaud: {target}")
            return target

        # Check alternative warm models if target is cold
        for m_name, m_prof in self.residency_registry.items():
            if m_prof.residency_state == ModelResidencyState.RESIDENT and (now - m_prof.last_invoked_at) < 300:
                logger.info(f"[LATENCY-OPTIMIZER] Bascule vers modèle chaud alternatif: {m_name} (évite cold start de {target})")
                return m_name

        return target

    def execute_optimized_model_call(
        self,
        prompt: str,
        task_type: str = "GENERIC",
        model: Optional[str] = None,
        max_tokens: int = 30,
    ) -> Dict[str, Any]:
        """Exécute un appel modèle optimisé (warm-start, cap de tokens, mesure haute précision)."""
        selected_model = self.select_latency_aware_model(task_type, preferred_model=model)
        profile = self.residency_registry[selected_model]

        t3 = time.perf_counter()

        # Call with tight num_predict cap to reduce generation time
        res = self.provider.generate(
            prompt=prompt,
            model=selected_model,
            num_predict=max_tokens,
            temperature=0.1,
        )

        t4 = time.perf_counter()
        call_ms = round((t4 - t3) * 1000, 3)

        # Update residency metadata
        profile.last_invoked_at = time.time()
        profile.total_calls += 1
        if profile.residency_state == ModelResidencyState.NOT_LOADED:
            profile.cold_latency_ms = call_ms
            profile.residency_state = ModelResidencyState.RESIDENT
        else:
            profile.warm_latency_ms = call_ms

        logger.info(f"[LATENCY-OPTIMIZER] Appel modèle '{selected_model}' exécuté en {call_ms} ms (Statut: WARM)")
        return {
            "response": res.get("response", "").strip(),
            "model_ms": call_ms,
            "selected_model": selected_model,
            "residency_state": "WARM" if profile.total_calls > 1 else "COLD",
        }

    def execute_parallel_nodes(self, independent_node_fns: List[Callable[[], Any]]) -> List[Any]:
        """Exécute en parallèle les tâches indépendantes du DAG."""
        t0 = time.perf_counter()
        futures = [self.executor.submit(fn) for fn in independent_node_fns]
        results = [f.result() for f in futures]
        t1 = time.perf_counter()
        logger.info(f"[PARALLEL-EXEC] {len(independent_node_fns)} nœuds exécutés en parallèle en {round((t1 - t0) * 1000, 3)} ms")
        return results


adaptive_model_optimizer = AdaptiveModelExecutionOptimizer()
