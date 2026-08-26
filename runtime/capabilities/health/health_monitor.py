"""
E-ZZIO V9.3.1 — Capability Health Monitor
Surveille l'homéostasie, la latence et la dérive de RAM des organes actifs.
"""

import json
from pathlib import Path

ROOT_DIR = Path(r"G:\AI\E-zzio")
HEALTH_STATE_PATH = ROOT_DIR / "runtime" / "capabilities" / "health" / "health_state.json"


class HealthMonitor:
    def __init__(self):
        self.state_file = HEALTH_STATE_PATH
        self._init_state()

    def _init_state(self):
        if not self.state_file.exists():
            initial = {
                "capability": "WEB_RESEARCHER",
                "health": {
                    "calls": 0,
                    "success": 0,
                    "errors": 0,
                    "avg_latency_ms": 12.0,
                    "ram_baseline_mb": 150.0,
                    "ram_current_mb": 150.0,
                    "status": "GREEN",
                },
            }
            self.state_file.write_text(json.dumps(initial, indent=2, ensure_ascii=False), encoding="utf-8")

    def get_health(self) -> dict:
        try:
            return json.loads(self.state_file.read_text(encoding="utf-8"))
        except Exception:
            return {}

    def record_call(self, success: bool, latency_ms: float, ram_usage_mb: float):
        data = self.get_health()
        h = data["health"]
        h["calls"] += 1
        if success:
            h["success"] += 1
        else:
            h["errors"] += 1

        h["avg_latency_ms"] = round((h["avg_latency_ms"] * (h["calls"] - 1) + latency_ms) / h["calls"], 2)
        h["ram_current_mb"] = float(ram_usage_mb)

        # Vérification des seuils d'homéostasie
        ram_drift = h["ram_current_mb"] - h["ram_baseline_mb"]
        if h["errors"] > 5 or ram_drift > 500:
            h["status"] = "CRITICAL"
        elif h["errors"] > 0 or ram_drift > 200:
            h["status"] = "WARNING"
        else:
            h["status"] = "GREEN"

        self.state_file.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
        return h
