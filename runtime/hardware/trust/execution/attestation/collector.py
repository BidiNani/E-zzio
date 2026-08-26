import psutil
from runtime.hardware.trust.execution.attestation.models import ObservationSnapshot


class RuntimeObservationCollector:
    @staticmethod
    def capture(pid: int) -> ObservationSnapshot:
        """Interroge l'OS (processus cible) pour capturer les métriques physiques réelles."""
        try:
            p = psutil.Process(pid)
            if not p.is_running():
                return ObservationSnapshot(
                    pid=pid, actual_affinity_mask=[], active_threads=0, peak_ram_mb=0.0, os_enforcement_verified=False, is_alive=False
                )

            # Capture de l'affinité réelle via l'OS
            affinity = p.cpu_affinity()
            threads_count = p.num_threads()

            # RAM RSS (Resident Set Size) en Mo
            mem_info = p.memory_info()
            peak_ram = round(mem_info.rss / (1024 * 1024), 2)

            return ObservationSnapshot(
                pid=pid,
                actual_affinity_mask=list(affinity),
                active_threads=threads_count,
                peak_ram_mb=peak_ram,
                os_enforcement_verified=True,
                is_alive=True,
            )
        except (psutil.NoSuchProcess, psutil.AccessDenied, Exception):
            return ObservationSnapshot(
                pid=pid, actual_affinity_mask=[], active_threads=0, peak_ram_mb=0.0, os_enforcement_verified=False, is_alive=False
            )
