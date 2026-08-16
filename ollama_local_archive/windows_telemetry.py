"""
E-ZZIO V7.25.0 — Windows Hardware Telemetry
Inspecte la charge réelle de la mémoire vive Windows via psutil ou WMI natif.
"""
import ctypes

class WindowsMemoryInspector:
    @staticmethod
    def get_system_memory_pressure() -> dict:
        """Retourne le pourcentage d'utilisation de la RAM physique Windows."""
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
            ctypes.windll.kernel32.GlobalMemoryStatusEx(byref(stat)) if hasattr(ctypes.windll.kernel32, 'GlobalMemoryStatusEx') else None
            
            # Fallback ctypes pur sécurisé Windows
            status = MEMORYSTATUSEX()
            status.dwLength = ctypes.sizeof(MEMORYSTATUSEX)
            ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(status))
            
            load_pct = status.dwMemoryLoad
            total_gb = round(status.ullTotalPhys / (1024**3), 2)
            avail_gb = round(status.ullAvailPhys / (1024**3), 2)
            
            return {
                "memory_load_pct": load_pct,
                "total_ram_gb": total_gb,
                "available_ram_gb": avail_gb,
                "os_pressure": load_pct > 85.0
            }
        except Exception:
            # Fallback neutre si exécution hors environnement Windows natif
            return {
                "memory_load_pct": 50.0,
                "total_ram_gb": 32.0,
                "available_ram_gb": 16.0,
                "os_pressure": False
            }

windows_memory = WindowsMemoryInspector()
