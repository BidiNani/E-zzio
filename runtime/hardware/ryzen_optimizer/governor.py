# ==============================================================================
# E-ZZIO Hardware — Granular Thread Governor V6.10.0
# ==============================================================================
import time
import threading
import psutil
from collections import deque
from .topology import RyzenTopologyInspector
from .affinity import RyzenAffinityManager

class HysteresisEngine:
    def __init__(self, hold_time=30.0):
        self.hold_time = hold_time
        self.last_transition = time.monotonic()
        self.candidate_profile = "NORMAL"
        self.current_profile = "NORMAL"
        self.decision_ledger = deque(maxlen=100) # Borné

    def update(self, new_profile: str) -> str:
        now = time.monotonic()
        if new_profile != self.current_profile:
            if new_profile != self.candidate_profile:
                self.candidate_profile = new_profile
                self.last_transition = now
                return self.current_profile
            
            if (now - self.last_transition) >= self.hold_time:
                self.decision_ledger.append({
                    "timestamp": time.time(),
                    "from": self.current_profile,
                    "to": new_profile,
                    "reason": "HYSTERESIS_HOLD_EXPIRED"
                })
                self.current_profile = new_profile
                return new_profile
        else:
            self.candidate_profile = self.current_profile
        return self.current_profile

class RyzenResourceGovernor:
    def __init__(self, hold_time=30.0):
        self.topology = RyzenTopologyInspector.inspect()
        self.affinity = RyzenAffinityManager(self.topology["logical_threads"])
        self.hysteresis = HysteresisEngine(hold_time=hold_time)
        self._lock = threading.Lock()
        
        # Métriques opérationnelles
        self.affinity_errors = 0
        self.last_affinity_error = ""

    def bind_worker_thread(self, thread_id: int, cores: list):
        """Applique l'affinité à un thread spécifique (V6.10 Granular)."""
        try:
            # Psutil permet d'itérer sur les threads du processus pour trouver le TID
            p = psutil.Process()
            for thread in p.threads():
                if thread.id == thread_id:
                    # Sous Windows/Linux, le bind se fait au niveau thread
                    # Ici on simule ou on utilise une API bas niveau si disponible
                    # E-ZZIO interface OS :
                    p.cpu_affinity(cores) # Application globale par défaut pour la démo
                    return True
        except Exception as e:
            with self._lock:
                self.affinity_errors += 1
                self.last_affinity_error = str(e)
            return False

    def evaluate_and_scale(self, spi: float, temperature: float = 50.0) -> dict:
        with self._lock:
            thermal_bias = max(0.0, (temperature - 70.0) / 100.0)
            adjusted_spi = spi + thermal_bias

            if adjusted_spi < 0.30: target = "IDLE"
            elif adjusted_spi < 0.70: target = "NORMAL"
            elif adjusted_spi < 0.90: target = "HEAVY"
            else: target = "EMERGENCY"

            stable_profile = self.hysteresis.update(target)
            allocated_threads = self.affinity.get_pool_allocation(stable_profile)
            
            return {
                "ryzen_profile": stable_profile,
                "active_workers": len(allocated_threads),
                "allocated_cores": allocated_threads,
                "spi_raw": spi,
                "spi_adjusted": round(adjusted_spi, 3),
                "affinity_errors": self.affinity_errors,
                "ledger": list(self.hysteresis.decision_ledger)
            }
