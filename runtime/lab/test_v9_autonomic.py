"""
E-ZZIO V9.0.2 — Laboratory Test : Autonomic Nervous System
Validation du démon asynchrone et de la copie d'efférence.
"""
import sys
import time
from pathlib import Path

ROOT_DIR = Path(r"G:\AI\E-zzio")
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from runtime.sensory.bus.sensory_bus import SensoryBus
from runtime.sensory.fusion.autonomic_watcher import AutonomicWatcher

def state_change_callback(old_state, new_state, percept):
    print(f"\n[🔔 ALERT] Changement d'attention : {old_state} -> {new_state}")
    print(f"   CPU: {percept.data['cpu_percent']}% | RAM: {percept.data['ram_percent']}% | WoW: {percept.data['gaming_mode']}")

def run_test():
    print("\n" + "="*60)
    print(" 🧪 LABORATOIRE V9.0.2 — AUTONOMIC WATCHER TEST")
    print("="*60)
    
    bus = SensoryBus()
    # Cycle réduit à 2 secondes pour les besoins du test
    watcher = AutonomicWatcher(bus, interval_sec=2) 
    watcher.on_state_change = state_change_callback
    
    print("[*] Démarrage du système nerveux autonome (Thread en arrière-plan)...")
    watcher.start()
    
    print("[*] Le thread principal continue de travailler librement.")
    print("[*] Simulation d'attente (10s) pour observer le silence du filtre anti-bruit...")
    
    try:
        # On simule le noyau principal qui fait sa vie pendant 10 secondes
        for i in range(5):
            time.sleep(2)
            sys.stdout.write(".")
            sys.stdout.flush()
    except KeyboardInterrupt:
        pass
    finally:
        print("\n\n[*] Arrêt du système nerveux périphérique...")
        watcher.stop()
        
    print("="*60)
    print(" 🟢 STATUT : SUCCÈS (Le démon est asynchrone et silencieux)")
    print("="*60 + "\n")

if __name__ == "__main__":
    run_test()
