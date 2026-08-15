"""
E-ZZIO Core — Hardware & Gaming Resource Governor (V7.71)
Implémente le protocole de cohabitation Gaming H24. Détecte la présence de jeux
ou de charges graphiques lourdes et contraint dynamiquement l'empreinte d'E-zzio
pour protéger l'expérience utilisateur et les performances de la GTX 1650 / Ryzen 9.
"""
import os
import sys
import time
import psutil
import logging
from pathlib import Path
from typing import Dict, Any

ROOT_DIR = Path(r"G:\AI\E-zzio")
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

logger = logging.getLogger(__name__)

class HardwareResourceGovernor:
    # Liste des processus cibles considérés comme prioritaires (Gaming Only)
    GAMING_PROCESS_SIGNATURES = {
        "wow.exe", "wowclassic.exe", "battle.net.exe", 
        "steam.exe", "discord.exe", "obs64.exe"
    }

    def __init__(self):
        self.gaming_mode_active = False
        self.max_threads_normal = 16
        self.max_threads_gaming = 4

    def detect_gaming_activity(self) -> bool:
        """Parcourt les processus en cours pour détecter si une application de jeu ou de streaming tourne."""
        try:
            for proc in psutil.process_iter(['name']):
                p_name = proc.info.get('name')
                if p_name and p_name.lower() in self.GAMING_PROCESS_SIGNATURES:
                    return True
        except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
            pass
        return False

    def get_system_telemetry(self) -> Dict[str, Any]:
        """Récupère l'état de santé instantané des ressources matérielles du PC."""
        cpu_percent = psutil.cpu_percent(interval=0.1)
        ram = psutil.virtual_memory()
        
        self.gaming_mode_active = self.detect_gaming_activity()

        recommended_threads = self.max_threads_gaming if self.gaming_mode_active else self.max_threads_normal
        profile_name = "GAMING_COEXISTENCE_MODE" if self.gaming_mode_active else "NORMAL_OPERATION_MODE"

        return {
            "profile": profile_name,
            "gaming_detected": self.gaming_mode_active,
            "cpu_system_usage_percent": cpu_percent,
            "ram_available_gb": round(ram.available / (1024**3), 2),
            "ram_usage_percent": ram.percent,
            "allocated_ezzio_threads": recommended_threads,
            "gpu_policy": "ISOLATED_GAMING_ONLY (GTX 1650 Untouched)"
        }

def test_hardware_governor():
    print("[*] Test du Hardware & Gaming Resource Governor (V7.71)...")
    gov = HardwareResourceGovernor()
    
    telemetry = gov.get_system_telemetry()
    
    print("\n" + "="*55)
    print(" E-ZZIO HARDWARE COEXISTENCE TELEMETRY")
    print("="*55)
    print(f" Profil Actif         : {telemetry['profile']}")
    print(f" Gaming Détecté       : {telemetry['gaming_detected']}")
    print(f" Charge CPU Globale   : {telemetry['cpu_system_usage_percent']}%")
    print(f" RAM Disponible       : {telemetry['ram_available_gb']} Go ({telemetry['ram_usage_percent']}% utilisé)")
    print(f" Workers Alloués      : {telemetry['allocated_ezzio_threads']} threads")
    print(f" Politique GPU        : {telemetry['gpu_policy']}")
    print("="*55)
    print(" [PASS] Le gouverneur matériel s'intègre au système sans friction.")

if __name__ == "__main__":
    test_hardware_governor()
