"""
E-ZZIO Core — Hardware Orchestration & Resource Governor (V8.2)
Orchestre activement les threads du Ryzen 9, surveille la pression RAM
et ajuste dynamiquement les quotas d'exécution des workers d'E-zzio.
"""

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


class ResourceExhaustionError(Exception):
    """Levée en cas de pression critique sur la RAM ou le CPU (Fail-Closed)."""

    pass


class HardwareOrchestrator:
    def __init__(self):
        self.hw_governor = HardwareResourceGovernor()
        self.gateway = EcolUniversalGateway()
        self.gateway.register_gateway_action("HARDWARE_RESOURCE_ALLOCATE")

    def allocate_execution_resources(self, task_name: str, requested_threads: int) -> Dict[str, Any]:
        """
        Alloue dynamiquement les ressources CPU/RAM en fonction du mode de vie (Gaming / Normal)
        et vérifie que l'organisme ne met pas en péril la stabilité de la machine.
        """
        telemetry = self.hw_governor.get_system_telemetry()
        is_gaming = telemetry["gaming_detected"]
        available_ram_gb = telemetry["ram_available_gb"]
        max_allowed_threads = telemetry["allocated_ezzio_threads"]

        # Sécurité anti-saturation RAM (Fail-Closed si moins de 4 Go disponibles)
        if available_ram_gb < 4.0:
            raise ResourceExhaustionError(
                f"FAIL CLOSED : Pression RAM critique ({available_ram_gb} Go disponibles). "
                f"Suspension immédiate des tâches lourdes pour protéger le système."
            )

        # Ajustement des threads selon le profil actif
        effective_threads = min(requested_threads, max_allowed_threads)

        payload = {
            "source_component": "system_core",
            "action": "HARDWARE_RESOURCE_ALLOCATE",
            "task_description": f"Allocation ressources pour '{task_name}' (Threads: {effective_threads})",
            "priority": "normal" if not is_gaming else "low",
            "risk_level": "low",
            "estimated_cost": effective_threads * 10,
        }

        def execute_allocation():
            return {
                "task_name": task_name,
                "threads_allocated": effective_threads,
                "profile_enforced": telemetry["profile"],
                "ram_status_gb": available_ram_gb,
                "gpu_status": telemetry["gpu_policy"],
                "status": "RESOURCES_ALLOCATED_SUCCESS",
            }

        # Validation No-Bypass via ECOL
        result = self.gateway.execute_via_gateway(action="HARDWARE_RESOURCE_ALLOCATE", payload=payload, target_func=execute_allocation)

        return result


def test_hardware_orchestrator():
    print("[*] Test de l'Hardware Orchestration Engine (V8.2)...")
    orchestrator = HardwareOrchestrator()

    print("\n--- Test 1 : Demande d'allocation de ressources (Ryzen 9 / RAM) ---")
    try:
        res = orchestrator.allocate_execution_resources("Vector_Indexation_Batch", requested_threads=12)
        print(f"  [PASS] Allocation réussie -> Threads alloués : {res['threads_allocated']} | Profil : {res['profile_enforced']}")
        print(f"         Politique GPU : {res['gpu_status']}")
    except Exception as e:
        print(f"  [FAIL] Erreur : {e}")

    print("\n" + "=" * 65)
    print(" HARDWARE ORCHESTRATION ENGINE (V8.2) : ACTIVE & COEXISTENCE-AWARE")
    print("=" * 65)


if __name__ == "__main__":
    test_hardware_orchestrator()
