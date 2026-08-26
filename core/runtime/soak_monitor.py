"""
E-ZZIO V7.47 — Soak Monitor & Memory Leak Detector
Surveille la consommation RAM et la stabilité sur une longue période d'exécution.
"""

import tracemalloc


class SoakMonitor:
    def __init__(self, memory_growth_threshold_mb: float = 50.0):
        self.threshold_mb = memory_growth_threshold_mb
        self.baseline_memory_mb = 0.0
        self.started = False

    def start_soak(self):
        tracemalloc.start()
        _, peak = tracemalloc.get_traced_memory()
        self.baseline_memory_mb = peak / (1024 * 1024)
        self.started = True

    def check_memory_drift(self) -> dict:
        if not self.started:
            self.start_soak()

        _, peak = tracemalloc.get_traced_memory()
        current_mb = peak / (1024 * 1024)
        drift = current_mb - self.baseline_memory_mb

        return {
            "baseline_mb": round(self.baseline_memory_mb, 4),
            "current_peak_mb": round(current_mb, 4),
            "drift_mb": round(drift, 4),
            "memory_leak_detected": drift > self.threshold_mb,
        }


soak_monitor = SoakMonitor()
