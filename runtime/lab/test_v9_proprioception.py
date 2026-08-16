"""
E-ZZIO V9.0.1 — Laboratory Test : Sensory Bus & Proprioception
Validation de la génération et du routage d'un Percept matériel.
"""
import sys
import time
import json
from pathlib import Path

# S'assurer que le chemin racine est dans le sys.path pour les imports
ROOT_DIR = Path(r"G:\AI\E-zzio")
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from runtime.sensory.bus.sensory_bus import SensoryBus
from runtime.sensory.sensors.proprioception_sensor import ProprioceptionSensor

def run_test():
    print("\n" + "="*50)
    print(" 🧪 LABORATOIRE V9.0.1 — SENSORY BUS TEST")
    print("="*50)
    
    start_time = time.perf_counter()

    try:
        # 1. Instanciation
        bus = SensoryBus()
        sensor = ProprioceptionSensor()

        # 2. Sensation (Capture)
        print("[*] Stimulation du capteur matériel...")
        percept = sensor.sense()

        # 3. Transmission
        print("[*] Transmission via le Sensory Bus...")
        bus.transmit(percept)

        # 4. Consommation
        percepts_in_bus = bus.consume_all()
        
        end_time = time.perf_counter()
        execution_ms = (end_time - start_time) * 1000

        print("\n📥 [PERCEPT REÇU]")
        if percepts_in_bus:
            print(json.dumps(percepts_in_bus[0], indent=2))
            print("-" * 50)
            print(f" ⏱️ Temps de cycle sensoriel : {execution_ms:.2f} ms")
            print(" 🟢 STATUT : SUCCÈS (Percept généré et routé)")
        else:
            print(" 🔴 STATUT : ÉCHEC (Aucun percept dans le bus)")
            
    except Exception as e:
        print(f" 🔴 ERREUR CRITIQUE : {str(e)}")
    
    print("="*50 + "\n")

if __name__ == "__main__":
    run_test()
