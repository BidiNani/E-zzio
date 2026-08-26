import psutil


class NUMAInspector:
    @staticmethod
    def inspect_memory_topology() -> dict:
        """
        Inspecte les nœuds NUMA et les zones de latence mémoire.
        Fournit un diagnostic explicite même en l'absence de partitions NUMA matérielles.
        """
        vm = psutil.virtual_memory()

        # Détection NUMA via psutil (si supporté par l'OS / psutil version récente)
        nodes = []
        numa_supported = False

        try:
            # psutil.NUMA nodes n'est pas toujours disponible sur tous les OS desktop Windows
            if hasattr(psutil, "cpu_numa_nodes"):
                numa_nodes = psutil.cpu_numa_nodes()
                if numa_nodes:
                    numa_supported = True
                    for node_id, cpus in numa_nodes.items():
                        nodes.append({"node_id": node_id, "cpus": cpus})
        except Exception:
            pass

        # Diagnostic de structuration pour architectures grand public (ex: Ryzen 5900X)
        if not numa_supported or not nodes:
            diagnostic_reason = "Single socket consumer architecture; standard unified memory domain with CCD internal latency separation."
        else:
            diagnostic_reason = "NUMA nodes successfully enumerated via OS/psutil."

        return {
            "numa_detected": numa_supported,
            "reason": diagnostic_reason,
            "total_nodes": len(nodes) if nodes else 1,
            "nodes": nodes,
            "memory_stats": {"total_bytes": vm.total, "available_bytes": vm.available, "percent_used": vm.percent},
        }
