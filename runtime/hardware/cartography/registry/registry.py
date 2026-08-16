import json
import time
from pathlib import Path
from runtime.hardware.cartography.snapshot_engine import CartographySnapshotEngine

class HardwareCartographyRegistry:
    def __init__(self, registry_dir: Path):
        self.registry_dir = registry_dir
        self.registry_dir.mkdir(parents=True, exist_ok=True)
        self.registry_file = self.registry_dir / "hardware_registry.json"
        self.snapshots_dir = self.registry_dir / "snapshots"
        self.snapshot_engine = CartographySnapshotEngine(self.snapshots_dir)

    def load_registry(self) -> dict:
        if not self.registry_file.exists():
            return {"baseline": None, "history": []}
        try:
            return json.loads(self.registry_file.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            return {"baseline": None, "history": []}

    def save_registry(self, data: dict):
        content = json.dumps(data, indent=4, ensure_ascii=False)
        self.registry_file.write_text(content, encoding="utf-8")

    def evaluate_and_update(self, current_map: dict) -> dict:
        """
        Évalue l'état matériel actuel face au registre, classifie les dérives 
        et historicise les événements.
        """
        registry = self.load_registry()
        baseline = registry.get("baseline")

        # 1. Initialisation de la Baseline si inexistante
        if baseline is None:
            json_path, file_hash = self.snapshot_engine.create_snapshot(current_map, tag="initial_baseline")
            registry["baseline"] = {
                "snapshot_file": json_path.name,
                "hash": file_hash,
                "topology": current_map,
                "registered_at": time.time()
            }
            registry["history"].append({
                "timestamp": time.time(),
                "event": "REGISTRY_INITIALIZED",
                "severity": "INFO",
                "category": "BOOT",
                "details": "Initial hardware truth established."
            })
            self.save_registry(registry)
            return {
                "status": "BASELINE_ESTABLISHED",
                "severity": "INFO",
                "category": "BOOT",
                "events": []
            }

        # 2. Comparaison avec la baseline enregistrée
        base_topo = baseline.get("topology", {})
        raw_drifts = self.snapshot_engine.detect_drift(base_topo, current_map)

        if not raw_drifts:
            return {
                "status": "MATCH",
                "severity": "NONE",
                "category": "NOMINAL",
                "events": []
            }

        # 3. Classification intelligente de la dérive (Change Intelligence)
        is_critical = any("THREADS" in d or "SMT" in d or "CORES" in d for d in raw_drifts)
        severity = "HIGH" if is_critical else "MEDIUM"
        category = "CPU_CONFIGURATION" if is_critical else "TOPOLOGY_CHANGE"

        event_record = {
            "timestamp": time.time(),
            "event": "HARDWARE_DRIFT_DETECTED",
            "severity": severity,
            "category": category,
            "events": raw_drifts,
            "action": "REQUIRE_REVALIDATION"
        }

        registry["history"].append(event_record)
        self.save_registry(registry)

        return {
            "status": "DRIFT_REGISTERED",
            "severity": severity,
            "category": category,
            "events": raw_drifts,
            "action": "REQUIRE_REVALIDATION"
        }
