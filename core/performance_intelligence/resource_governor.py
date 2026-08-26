"""
E-ZZIO V7.38 — Adaptive Resource Governor
Gouverneur de ressources : lit l'état matériel (CPU/RAM) et adapte dynamiquement
la topologie (workers, mode d'exécution, budget mémoire).
"""

import os
import platform
import ctypes


class ResourceGovernor:
    def __init__(self):
        self.cpu_threads = os.cpu_count() or 4
        self.memory_budget_margin = 0.20  # Conserve toujours 20% de RAM libre pour l'OS

    def get_available_ram_mb(self) -> float:
        """Lecture native de la mémoire physique disponible (Windows fallback)."""
        if platform.system() == "Windows":
            try:

                class MEMORYSTATUSEX(ctypes.Structure):
                    _fields_ = [
                        ("dwLength", ctypes.c_ulong),
                        ("dwMemoryLoad", ctypes.c_ulong),
                        ("ullTotalPhys", ctypes.c_ulonglong),
                        ("ullAvailPhys", ctypes.c_ulonglong),
                        ("ullTotalPageFile", ctypes.c_ulonglong),
                        ("ullAvailPageFile", ctypes.c_ulonglong),
                        ("ullTotalVirtual", ctypes.c_ulonglong),
                        ("ullAvailVirtual", ctypes.c_ulonglong),
                        ("sullAvailExtendedVirtual", ctypes.c_ulonglong),
                    ]

                stat = MEMORYSTATUSEX()
                stat.dwLength = ctypes.sizeof(MEMORYSTATUSEX)
                ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(stat))
                return stat.ullAvailPhys / (1024 * 1024)
            except Exception:
                pass
        return 8192.0  # Fallback de sécurité à 8GB si OS non Windows ou erreur

    def evaluate_topology(self, simulated_ram_mb: float = None) -> dict:
        ram_mb = simulated_ram_mb if simulated_ram_mb is not None else self.get_available_ram_mb()

        # Arbre de décision des politiques de ressources
        if ram_mb < 2048 or self.cpu_threads <= 2:
            mode = "PERFORMANCE_SAFE"
            workers = 1
        elif ram_mb < 8192:
            mode = "CONSERVATIVE"
            workers = max(1, self.cpu_threads // 2)
        else:
            mode = "MAX_PERFORMANCE"
            workers = max(1, self.cpu_threads - 2)  # Garde 2 threads pour le système

        return {
            "cpu_threads": self.cpu_threads,
            "free_ram_gb": round(ram_mb / 1024, 2),
            "workers_selected": workers,
            "mode": mode,
            "allocatable_ram_mb": round(ram_mb * (1.0 - self.memory_budget_margin), 2),
        }

    def enforce_memory_budget(self, requested_mb: float, simulated_ram_mb: float = None) -> bool:
        """Vérifie si une opération peut être lancée sans saturer le système."""
        topology = self.evaluate_topology(simulated_ram_mb)
        return requested_mb <= topology["allocatable_ram_mb"]


resource_governor = ResourceGovernor()
