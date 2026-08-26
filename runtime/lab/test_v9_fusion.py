"""
E-ZZIO V9.0.3 — Laboratory Test : Fusion Engine
Validation de l'assemblage d'un contexte sensoriel unifié.
"""

import sys
import time
import json
from pathlib import Path

ROOT_DIR = Path(r"G:\AI\E-zzio")
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from runtime.sensory.bus.sensory_bus import SensoryBus
from runtime.sensory.fusion.autonomic_watcher import AutonomicWatcher
from runtime.sensory.fusion.fusion_engine import FusionEngine


def run_test():
    print("\n" + "=" * 60)
    print(" 🧪 LABORATOIRE V9.0.3 — SENSORY FUSION TEST")
    print("=" * 60)

    bus = SensoryBus()
    fusion = FusionEngine(bus)
    watcher = AutonomicWatcher(bus, interval_sec=1)

    print("[*] Activation de la proprioception (Autonomic Watcher)...")
    watcher.start()

    # On laisse le temps au démon de faire au moins un battement (capture)
    time.sleep(1.5)

    print("[*] Demande de situation unifiée au Fusion Engine...")
    situation = fusion.get_current_situation()

    watcher.stop()

    print("\n🧠 [SITUATION FUSIONNÉE]")
    print(json.dumps(situation, indent=2))

    if "hardware_sensor" in situation["modalities"]:
        print("-" * 60)
        print(" 🟢 STATUT : SUCCÈS (Le Moteur de Fusion agrège correctement les sens)")
    else:
        print(" 🔴 STATUT : ÉCHEC (Modalité manquante dans la fusion)")
    print("=" * 60 + "\n")


if __name__ == "__main__":
    run_test()
