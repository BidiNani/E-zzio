# ==============================================================================
# E-ZZIO — Worker Bootstrap & Governor Enforcement Engine v1.0
# File: G:\AI\E-zzio\runtime\execution\worker_bootstrap.py
# ==============================================================================
import os
import sys
import json
import logging
from pathlib import Path
from concurrent.futures import ProcessPoolExecutor, ThreadPoolExecutor

ROOT_PATH = Path(r"G:\AI\E-zzio")
sys.path.insert(0, str(ROOT_PATH))

from core.constitution.hardware_resource_governor import HardwareResourceGovernor

class EzzioWorkerManager:
    """Gestionnaire centralisé des workers E-ZZIO sous supervision du Governor."""
    def __init__(self):
        self.hw_governor = HardwareResourceGovernor()
        self.profile_name = "GamingOptimized"
        self.max_ram_gb = 10
        self.max_workers = 8
        self.process_pool = None
        self.thread_pool = None
        self.status = "INITIALIZING"

    def initialize_pool(self):
        logging.info(f"[*] Initialisation Worker Pool [{self.profile_name}] — Plafond RAM: {self.max_ram_gb} GB, Max Workers: {self.max_workers}")
        
        # Vérification de la télémétrie matérielle via le Governor
        telemetry = self.hw_governor.get_system_telemetry()
        available_ram_gb = telemetry.get("ram_available_gb", 16)
        
        if available_ram_gb < 2.0:
            logging.warning("[!] RAM disponible faible (< 2 Go). Réduction préventive à 2 workers.")
            active_worker_count = 2
        else:
            active_worker_count = self.max_workers

        # Pool d'exécuteurs de tâches
        self.process_pool = ProcessPoolExecutor(max_workers=active_worker_count)
        self.thread_pool = ThreadPoolExecutor(max_workers=active_worker_count * 2)
        self.status = "ONLINE"
        
        logging.info(f"[OK] Worker Manager actif avec {active_worker_count} process workers et {active_worker_count * 2} async threads.")
        return {
            "status": self.status,
            "profile": self.profile_name,
            "max_ram_gb": self.max_ram_gb,
            "active_workers": active_worker_count
        }

    def shutdown(self):
        logging.info("[*] Arrêt du Worker Pool E-ZZIO...")
        if self.process_pool:
            self.process_pool.shutdown(wait=False)
        if self.thread_pool:
            self.thread_pool.shutdown(wait=False)
        self.status = "OFFLINE"

# Instance globale réutilisable par l'API
worker_manager = EzzioWorkerManager()

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    res = worker_manager.initialize_pool()
    print(json.dumps(res, indent=2))
