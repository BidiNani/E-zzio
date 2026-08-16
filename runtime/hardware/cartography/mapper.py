import psutil
import platform
from runtime.hardware.cartography.numa import NUMAInspector

try:
    import cpuinfo
except ImportError:
    cpuinfo = None

class HardwareTopologyMapper:
    @staticmethod
    def generate_map(trusted_probe: dict) -> dict:
        """
        Génère une cartographie interne enrichie incluant la topologie NUMA et mémoire.
        """
        if not trusted_probe or "cpu" not in trusted_probe:
            raise ValueError("INVALID_PROBE_DATA: Missing CPU core/thread information")

        cpu_meta = trusted_probe.get("cpu", {})
        clusters = trusted_probe.get("clusters", {})
        
        raw_info = {}
        if cpuinfo is not None:
            try:
                raw_info = cpuinfo.get_cpu_info()
            except Exception:
                pass
        
        # Inspection NUMA / Mémoire granulaire
        numa_topology = NUMAInspector.inspect_memory_topology()
        
        mapped_structure = {
            "system": {
                "os": platform.system(),
                "release": platform.release(),
                "architecture": platform.machine()
            },
            "cpu": {
                "vendor": raw_info.get("vendor_id_raw", platform.processor() or "Unknown"),
                "model": raw_info.get("brand_raw", platform.processor() or "Unknown Ryzen/Processor"),
                "physical_cores": cpu_meta.get("physical", psutil.cpu_count(logical=False)),
                "logical_threads": cpu_meta.get("logical", psutil.cpu_count(logical=True)),
                "smt": cpu_meta.get("logical", 0) > cpu_meta.get("physical", 0)
            },
            "clusters": clusters,
            "memory": numa_topology,
            "cache": {
                "l3_size": raw_info.get("l3_cache_size", "Unknown"),
                "l2_size": raw_info.get("l2_cache_size", "Unknown"),
                "l1_size": raw_info.get("l1_cache_size", "Unknown")
            }
        }
        return mapped_structure
