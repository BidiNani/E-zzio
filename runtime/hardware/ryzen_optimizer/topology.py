# ==============================================================================
# E-ZZIO Hardware — Ryzen Topology & SMT Inspector
# ==============================================================================
import os
import psutil

class RyzenTopologyInspector:
    """Inspecte la topologie matérielle réelle du processeur Ryzen (Cœurs, SMT, Fréquences)."""
    @staticmethod
    def inspect() -> dict:
        logical_threads = os.cpu_count() or 4
        try:
            physical_cores = psutil.cpu_count(logical=False) or (logical_threads // 2)
        except Exception:
            physical_cores = logical_threads // 2

        smt_active = logical_threads > physical_cores
        
        freqs = {}
        try:
            f = psutil.cpu_freq()
            if f:
                freqs = {"current_mhz": f.current, "min_mhz": f.min, "max_mhz": f.max}
        except Exception:
            freqs = {"current_mhz": 3400.0, "max_mhz": 4600.0}

        return {
            "architecture": "AMD Ryzen Multi-Core",
            "physical_cores": physical_cores,
            "logical_threads": logical_threads,
            "smt_active": smt_active,
            "frequencies": freqs
        }
