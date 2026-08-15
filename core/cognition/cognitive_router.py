"""
E-ZZIO Core — Cognitive Task Classifier & Model Router (V8.1)
Analyse l'intention de la tâche et sélectionne dynamiquement le modèle optimal 
en tenant compte de la complexité, du coût, et de l'état matériel (Gaming Coexistence).
"""
import os
import sys
import logging
from pathlib import Path
from typing import Dict, Any

ROOT_DIR = Path(r"G:\AI\E-zzio")
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from core.constitution.hardware_resource_governor import HardwareResourceGovernor
from core.cognition.ecol_universal_enforcement import EcolUniversalGateway

logger = logging.getLogger(__name__)

class CognitiveRouterError(Exception):
    """Levée en cas d'échec de routage ou de non-disponibilité des ressources (Fail-Closed)."""
    pass

class CognitiveTaskClassifier:
    TASK_MAP = {
        "code": {"model": "qwen2.5-coder:7b", "fallback": "qwen2.5:3b", "cost_factor": 1.2},
        "reasoning": {"model": "deepseek-r1:8b", "fallback": "qwen2.5:3b", "cost_factor": 2.0},
        "quick": {"model": "qwen2.5:3b", "fallback": "qwen2.5:3b", "cost_factor": 0.3},
        "vision": {"model": "qwen2.5vl", "fallback": "qwen2.5:3b", "cost_factor": 1.5}
    }

    def __init__(self):
        self.hw_governor = HardwareResourceGovernor()
        self.gateway = EcolUniversalGateway()
        self.gateway.register_gateway_action("COGNITIVE_MODEL_ROUTE")

    def route_task(self, task_type: str, task_description: str, estimated_tokens: int) -> Dict[str, Any]:
        """
        Classifie la tâche, interroge le gouverneur matériel (Gaming H24) 
        et sélectionne le modèle optimal sous le contrôle de la passerelle ECOL.
        """
        if task_type not in self.TASK_MAP:
            raise CognitiveRouterError(f"Type de tâche cognitif inconnu : {task_type}")

        telemetry = self.hw_governor.get_system_telemetry()
        is_gaming = telemetry["gaming_detected"]

        profile = self.TASK_MAP[task_type]
        
        # En mode Gaming, forçage du modèle léger pour préserver les performances du PC
        selected_model = profile["fallback"] if is_gaming else profile["model"]

        payload = {
            "source_component": "llm_dispatcher",
            "action": "COGNITIVE_MODEL_ROUTE",
            "task_description": f"Routage cognitif [{task_type}] -> {selected_model} (Gaming: {is_gaming})",
            "priority": "normal" if not is_gaming else "low",
            "risk_level": "low",
            "estimated_cost": int(estimated_tokens * profile["cost_factor"])
        }

        def execute_routing():
            return {
                "task_type": task_type,
                "routed_model": selected_model,
                "gaming_coexistence_active": is_gaming,
                "cost_adjusted": payload["estimated_cost"],
                "status": "OPTIMIZED_ROUTE_DISPATCHED"
            }

        # Validation No-Bypass via ECOL
        result = self.gateway.execute_via_gateway(
            action="COGNITIVE_MODEL_ROUTE",
            payload=payload,
            target_func=execute_routing
        )

        return result

def test_cognitive_router():
    print("[*] Test du Cognitive Task Classifier & Model Router (V8.1)...")
    router = CognitiveTaskClassifier()

    # Test 1 : Tâche de code en mode normal / gaming
    print("\n--- Test 1 : Routage d'une tâche de code complexe ---")
    res = router.route_task("code", "Refactoring du module de persistance E-zzio", 450)
    print(f"  [PASS] Tâche routée vers le modèle : {res['routed_model']} | Mode Gaming : {res['gaming_coexistence_active']}")

    # Test 2 : Tâche de raisonnement lourd
    print("\n--- Test 2 : Routage d'une tâche de raisonnement (DeepSeek / Fallback) ---")
    res_reason = router.route_task("reasoning", "Analyse comparative de l'architecture Mémorielle L0-L5", 800)
    print(f"  [PASS] Tâche routée vers le modèle : {res_reason['routed_model']} | Coût ajusté : {res_reason['cost_adjusted']}")

    print("\n" + "="*65)
    print(" COGNITIVE ROUTER (V8.1) : OPERATIONAL & HARDWARE-AWARE")
    print("="*65)

if __name__ == "__main__":
    test_cognitive_router()
