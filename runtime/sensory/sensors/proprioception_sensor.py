"""
E-ZZIO V9 — Proprioception Sensor (Hardware Sense)
Le sens interne de l'organisme. Surveille les constantes vitales et détermine l'attention requise.
"""
import psutil
from runtime.sensory.bus.percept import Percept

class ProprioceptionSensor:
    def __init__(self):
        self.name = "hardware_sensor"

    def _check_wow_running(self) -> bool:
        for p in psutil.process_iter(['name']):
            try:
                if p.info['name'] and 'wow.exe' in p.info['name'].lower():
                    return True
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                pass
        return False

    def sense(self) -> Percept:
        cpu = psutil.cpu_percent(interval=0.1)
        ram = psutil.virtual_memory().percent
        g_disk = psutil.disk_usage(r"G:")
        g_free = round(g_disk.free / (1024**3), 2)
        gaming_mode = self._check_wow_running()

        # Mécanisme d'attention dynamique (Sensory Gating)
        attention_budget = "LOW"
        if cpu > 85.0 or ram > 85.0:
            attention_budget = "HIGH"
        elif cpu > 50.0 or gaming_mode:
            attention_budget = "MEDIUM"

        data = {
            "cpu_percent": cpu,
            "ram_percent": ram,
            "nvme_free_gb": g_free,
            "gaming_mode": gaming_mode,
            "attention_budget_required": attention_budget
        }

        return Percept(source=self.name, data=data, priority=attention_budget)
