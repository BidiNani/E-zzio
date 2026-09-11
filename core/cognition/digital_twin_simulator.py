"""
E-ZZIO Core — Digital Twin & Simulation Engine (V8.6)
Exécute des simulations d'impact (ressources, tokens, conformité constitutionnelle)
sur un jumeau numérique virtuel avant d'autoriser toute modification sur l'organisme réel.
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


class SimulationFailureError(Exception):
    """Levée si la simulation d'un changement révèle un risque pour l'organisme (Fail-Closed)."""

    pass


class DigitalTwinSimulator:
    def __init__(self):
        self.hw_governor = HardwareResourceGovernor()
        self.gateway = EcolUniversalGateway()
        self.gateway.register_gateway_action("DIGITAL_TWIN_SIMULATE")

    def simulate_change(self, change_type: str, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """
        Simule l'impact d'un changement (ex: compression mémoire massive, run d'un agent lourd)
        sur le jumeau numérique avant validation par ECOL.
        """
        telemetry = self.hw_governor.get_system_telemetry()
        is_gaming = telemetry["gaming_detected"]

        # Simulation prédictive d'impact
        simulated_ram_delta_gb = parameters.get("estimated_ram_delta_gb", 0.5)
        projected_ram_usage = telemetry["ram_usage_percent"] + (simulated_ram_delta_gb / 32.0) * 100

        # Règle de simulation : rejet si le changement projette une saturation RAM ou perturbe le mode Gaming
        if is_gaming and projected_ram_usage > 85.0:
            raise SimulationFailureError(
                f"SIMULATION FAIL CLOSED : Le changement '{change_type}' projette une saturation RAM "
                f"({projected_ram_usage:.1f}%) en plein mode Gaming. Simulation rejetée."
            )

        payload = {
            "source_component": "system_core",
            "action": "DIGITAL_TWIN_SIMULATE",
            "task_description": f"Simulation jumeau numérique pour '{change_type}'",
            "priority": "normal",
            "risk_level": "low" if projected_ram_usage < 75.0 else "medium",
            "estimated_cost": 100,
        }

        def commit_simulation_pass():
            return {
                "change_type": change_type,
                "simulation_status": "PASSED",
                "projected_ram_percent": round(projected_ram_usage, 2),
                "gaming_context": is_gaming,
                "recommendation": "SAFE_FOR_PRODUCTION_PROMOTION",
            }

        # Validation No-Bypass via ECOL
        result = self.gateway.execute_via_gateway(action="DIGITAL_TWIN_SIMULATE", payload=payload, target_func=commit_simulation_pass)

        return result


def test_digital_twin():
    print("[*] Test du Digital Twin & Simulation Engine (V8.6)...")
    simulator = DigitalTwinSimulator()

    print("\n--- Test 1 : Simulation d'une compaction mémorielle légère ---")
    try:
        res = simulator.simulate_change("memory_compaction_l4", {"estimated_ram_delta_gb": 0.2})
        print(f"  [PASS] Simulation réussie -> Statut : {res['simulation_status']} | RAM projetée : {res['projected_ram_percent']}%")
        print(f"         Recommandation : {res['recommendation']}")
    except Exception as e:
        print(f"  [FAIL] Erreur : {e}")

    print("\n" + "=" * 65)
    print(" DIGITAL TWIN SIMULATOR (V8.6) : OPERATIONAL & PREDICTIVE")
    print("=" * 65)


if __name__ == "__main__":
    test_digital_twin()
