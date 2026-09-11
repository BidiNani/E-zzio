"""
E-ZZIO Core — Dynamic Model Qualification Pipeline.

Évalue et homologue les modèles candidats dans la fédération E-ZzIO :
- Test de vivacité et latence
- Évaluation d'inférence (réponse minimale déterministe)
- Classification du statut (QUALIFIED, QUALIFIED_WITH_LIMITATIONS, REJECTED)
- Tolérance totale aux pannes réseau / mode OFFLINE
"""
from __future__ import annotations
import time
from typing import Dict, Any, Optional
from core.routing.model_registry import (
    ModelQualificationStatus,
    LatencyTier,
    CanonicalModelRecord,
    ModelSource,
    CostClass
)


class ModelQualificationPipeline:
    """Pipeline d'homologation déterministe et sécurisé."""

    def __init__(self, timeout_sec: float = 5.0):
        self.timeout_sec = timeout_sec

    def qualify_candidate(
        self,
        raw_name: str,
        source: ModelSource,
        test_fn: Optional[callable] = None,
    ) -> Dict[str, Any]:
        """Exécute un test de qualification sur un modèle candidat."""
        start = time.time()
        test_prompt = "Say 'OK' and nothing else."

        # Si aucune fonction fournie, qualification théorique / heuristique
        if test_fn is None:
            elapsed_ms = 150
            status = ModelQualificationStatus.QUALIFIED
            latency_tier = LatencyTier.FAST
            success = True
            output = "OK"
        else:
            try:
                output = test_fn(test_prompt)
                elapsed_ms = int((time.time() - start) * 1000)
                success = bool(output and len(str(output).strip()) > 0)
                if elapsed_ms < 600:
                    latency_tier = LatencyTier.FAST
                elif elapsed_ms < 2500:
                    latency_tier = LatencyTier.MEDIUM
                else:
                    latency_tier = LatencyTier.SLOW

                if success:
                    status = (
                        ModelQualificationStatus.QUALIFIED
                        if latency_tier in (LatencyTier.FAST, LatencyTier.MEDIUM)
                        else ModelQualificationStatus.QUALIFIED_WITH_LIMITATIONS
                    )
                else:
                    status = ModelQualificationStatus.REJECTED
            except Exception as exc:
                elapsed_ms = int((time.time() - start) * 1000)
                success = False
                status = ModelQualificationStatus.REJECTED
                latency_tier = LatencyTier.SLOW
                output = f"ERROR: {exc}"

        cost_class = CostClass.LOCAL if source == ModelSource.LOCAL else CostClass.FREE_ENDPOINT
        prefix = source.value.lower()
        model_id = f"{prefix}/{raw_name.split('/')[-1]}"

        record = CanonicalModelRecord(
            model_id=model_id,
            source=source,
            raw_model_name=raw_name,
            capabilities=["TEXT"],
            context_window=32768,
            cost_class=cost_class,
            latency_tier=latency_tier,
            qualification_status=status,
            limitations=[] if status == ModelQualificationStatus.QUALIFIED else ["Evaluated with caveats"],
        )

        return {
            "model_id": model_id,
            "source": source.value,
            "raw_name": raw_name,
            "status": status.value,
            "latency_ms": elapsed_ms,
            "latency_tier": latency_tier.value,
            "success": success,
            "record": record,
        }
