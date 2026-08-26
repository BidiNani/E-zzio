import platform
import urllib.request


class SystemSensor:
    """Capteur de perception système et matériel."""

    def __init__(self, ollama_url="http://localhost:11434"):
        self.ollama_url = ollama_url

    def scan(self) -> dict:
        ram_total = "Inconnu"
        ram_available = "Inconnu"
        try:
            import ctypes

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
                    ("ullExtendedVirtualInformation", ctypes.c_ulonglong),
                ]

            stat = MEMORYSTATUSEX()
            stat.dwLength = ctypes.sizeof(MEMORYSTATUSEX)
            ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(stat))
            ram_total = f"{round(stat.ullTotalPhys / (1024**3), 1)}GB"
            ram_available = f"{round(stat.ullAvailPhys / (1024**3), 1)}GB"
        except Exception:
            pass

        ollama_online = False
        try:
            req = urllib.request.Request(f"{self.ollama_url}/api/tags")
            with urllib.request.urlopen(req, timeout=2) as resp:
                ollama_online = resp.status == 200
        except Exception:
            ollama_online = False

        return {
            "cpu": {"processor": platform.processor(), "machine": platform.machine(), "system": platform.system()},
            "memory": {"total": ram_total, "available": ram_available},
            "gpu": {"name": "GTX 1650 (Local)", "policy": "CPU-only / Optimisé"},
            "python": platform.python_version(),
            "ollama": ollama_online,
        }
