import json
import hashlib
import time
from pathlib import Path


class CartographySnapshotEngine:
    def __init__(self, snapshots_dir: Path):
        self.snapshots_dir = snapshots_dir
        self.snapshots_dir.mkdir(parents=True, exist_ok=True)

    def _deterministic_payload(self, topology_map: dict) -> dict:
        """Extrait les données structurelles fixes pour le hachage (exclut les timestamps)."""
        return {
            "cpu": topology_map.get("cpu", {}),
            "clusters": topology_map.get("clusters", {}),
            "memory_nodes_count": topology_map.get("memory", {}).get("total_nodes", 1),
        }

    def create_snapshot(self, topology_map: dict, tag: str = "topology") -> tuple:
        """Crée un snapshot signé de la cartographie matérielle."""
        timestamp_str = time.strftime("%Y%m%d_%H%M%S")
        base_name = f"{tag}_{timestamp_str}"

        json_path = self.snapshots_dir / f"{base_name}.json"
        hash_path = self.snapshots_dir / f"{base_name}.hash"

        snapshot_data = {"version": "6.13.2", "timestamp": time.time(), "formatted_time": timestamp_str, "topology": topology_map}

        # Écriture du JSON
        json_content = json.dumps(snapshot_data, indent=4, ensure_ascii=False)
        json_path.write_text(json_content, encoding="utf-8")

        # Génération du hash SHA-256 déterministe
        payload = self._deterministic_payload(topology_map)
        payload_encoded = json.dumps(payload, sort_keys=True).encode("utf-8")
        computed_hash = hashlib.sha256(payload_encoded).hexdigest()

        # Écriture du fichier de hash compagnon
        hash_path.write_text(computed_hash, encoding="utf-8")

        return json_path, computed_hash

    @staticmethod
    def detect_drift(baseline_map: dict, current_map: dict) -> list:
        """Compare deux cartographies et retourne la liste des dérives structurelles."""
        drifts = []

        base_cpu = baseline_map.get("cpu", {})
        curr_cpu = current_map.get("cpu", {})

        if base_cpu.get("logical_threads") != curr_cpu.get("logical_threads"):
            drifts.append("LOGICAL_THREADS_MISMATCH")

        if base_cpu.get("physical_cores") != curr_cpu.get("physical_cores"):
            drifts.append("PHYSICAL_CORES_MISMATCH")

        if base_cpu.get("smt") != curr_cpu.get("smt"):
            drifts.append("SMT_STATE_CHANGED")

        base_clusters = baseline_map.get("clusters", {})
        curr_clusters = current_map.get("clusters", {})

        if set(base_clusters.keys()) != set(curr_clusters.keys()):
            drifts.append("CCD_TOPOLOGY_STRUCTURE_CHANGED")

        return drifts
