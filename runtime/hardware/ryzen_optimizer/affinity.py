# ==============================================================================
# E-ZZIO Hardware — Ryzen Thread Affinity Pool Manager
# ==============================================================================
class RyzenAffinityManager:
    """
    Gère la répartition des 24 threads du Ryzen en trois pools dynamiques :
    - Pool 0 (Reserved) : Threads 0 à 3 (Services OS / Watchdog critique)
    - Pool 1 (Normal)   : Threads 4 à 15 (E-ZZIO Ingestion & Moteur standard)
    - Pool 2 (Burst)    : Threads 16 à 23 (Analyse lourde / Recovery d'urgence)
    """
    def __init__(self, total_threads: int = 24):
        self.total_threads = total_threads
        self.pools = {
            "RESERVED": list(range(0, min(4, total_threads))),
            "NORMAL": list(range(4, min(16, total_threads))),
            "BURST": list(range(16, total_threads)) if total_threads > 16 else []
        }

    def get_pool_allocation(self, workload_intensity: str) -> list[int]:
        intensity = workload_intensity.upper()
        if intensity == "IDLE":
            return self.pools["RESERVED"] + self.pools["NORMAL"][:2]
        elif intensity == "NORMAL":
            return self.pools["RESERVED"] + self.pools["NORMAL"]
        elif intensity in ["HEAVY", "BURST"]:
            return self.pools["RESERVED"] + self.pools["NORMAL"] + self.pools["BURST"]
        elif intensity == "EMERGENCY":
            return list(range(0, self.total_threads)) # All-in pour sauver le runtime
        return self.pools["RESERVED"] + self.pools["NORMAL"]
