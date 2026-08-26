import psutil
import time
import json


class HardwareDiscovery:
    @staticmethod
    def probe():
        """Scanne la topologie matérielle réelle."""
        logical = psutil.cpu_count(logical=True)
        physical = psutil.cpu_count(logical=False)

        # Détection basique des groupes de cœurs (Affinité)
        # Sur Ryzen, psutil expose les cœurs par ordre logique
        data = {
            "version": "1.0",
            "timestamp": time.time(),
            "cpu": {"logical_threads": logical, "physical_cores": physical, "smt": logical > physical},
            "topology_clusters": {"CLUSTER_A": list(range(0, logical // 2)), "CLUSTER_B": list(range(logical // 2, logical))},
        }
        return data

    @staticmethod
    def save_report(data):
        report_path = "runtime/experiments/v611_topology/hardware_report.json"
        with open(report_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=4)
        return report_path
