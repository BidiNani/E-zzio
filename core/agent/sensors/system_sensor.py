"""E-ZZIO Autonomous Agent — Host Hardware & Runtime Telemetry Sensor."""
from __future__ import annotations

import json
import os
import shutil
import urllib.request
from typing import Any

import psutil


class SystemSensor:
    def __init__(self, workspace_root: str = "G:\\AI\\E-zzio"):
        self.workspace_root = workspace_root

    def _query_ollama(self, endpoint: str) -> Any:
        try:
            req = urllib.request.Request(
                f"http://127.0.0.1:11434{endpoint}",
                headers={"Content-Type": "application/json"}
            )
            with urllib.request.urlopen(req, timeout=1.5) as resp:
                if resp.status == 200:
                    return json.loads(resp.read().decode("utf-8"))
        except Exception:
            return None
        return None

    def get_system_telemetry(self) -> dict[str, Any]:
        """Collecte les métriques matérielles et distingue modèles installés vs actifs."""
        cpu_pct = psutil.cpu_percent(interval=0.1)
        mem = psutil.virtual_memory()

        drive = os.path.splitdrive(os.path.abspath(self.workspace_root))[0] or "G:"
        disk = shutil.disk_usage(drive)

        # 1. Modèles installés sur disque (/api/tags)
        tags_data = self._query_ollama("/api/tags")
        installed_models = [m.get("name") for m in tags_data.get("models", [])] if tags_data else []

        # 2. Modèles actuellement chargés en RAM/VRAM (/api/ps)
        ps_data = self._query_ollama("/api/ps")
        running_models = []
        if ps_data and "models" in ps_data:
            for rm in ps_data["models"]:
                running_models.append({
                    "name": rm.get("name"),
                    "size_vram_gb": round(rm.get("size_vram", 0) / (1024 ** 3), 2),
                    "expires_at": rm.get("expires_at")
                })

        ollama_status = "ACTIVE" if tags_data is not None else "INACCESSIBLE"

        return {
            "cpu": {
                "usage_percent": cpu_pct,
                "cores_logical": psutil.cpu_count(logical=True)
            },
            "memory": {
                "total_gb": round(mem.total / (1024 ** 3), 2),
                "available_gb": round(mem.available / (1024 ** 3), 2),
                "used_percent": mem.percent
            },
            "disk": {
                "drive": drive,
                "free_gb": round(disk.free / (1024 ** 3), 2),
                "total_gb": round(disk.total / (1024 ** 3), 2)
            },
            "ollama": {
                "status": ollama_status,
                "models_installed": installed_models,
                "models_running_in_memory": running_models
            }
        }
