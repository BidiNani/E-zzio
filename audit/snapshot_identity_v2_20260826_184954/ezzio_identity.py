from __future__ import annotations

import os
import sys
import time
from pathlib import Path
from typing import Any, Dict

PROJECT_ROOT = Path("G:/AI/E-zzio")

CPU_ONLY_ENV = {
    "OLLAMA_NUM_GPU": "0",
    "CUDA_VISIBLE_DEVICES": "",
    "GGML_CUDA": "0",
    "CUDA_DEVICE_ORDER": "PCI_BUS_ID",
    "EZZIO_GPU_POLICY": "cpu_ram_only",
    "EZZIO_NUM_GPU": "0",
    "PYTORCH_ENABLE_MPS_FALLBACK": "0",
    "EZZIO_NO_ADS": "true",
    "EZZIO_NO_TRACKING": "true",
    "EZZIO_NO_SPONSORS": "true",
}

for key, value in CPU_ONLY_ENV.items():
    os.environ[key] = value


def identity_payload() -> Dict[str, Any]:
    return {
        "ok": True,
        "name": "E-ZZIO",
        "version": "v2.14-root-identity-route-audit",
        "created_at": time.strftime("%Y-%m-%dT%H:%M:%S"),
        "project_root": str(PROJECT_ROOT),
        "identity": {
            "type": "local_ai_companion",
            "owner": "Enrik",
            "mission": "Être un organisme IA local utile, fiable, partout où Enrik le décide.",
            "presence": [
                "PC local",
                "API locale",
                "smartphone LAN bridge",
                "Discord officiel si configuré",
                "Messenger officiel si configuré",
                "Vision",
                "Forge",
                "Supervisor",
                "Watchdog",
            ],
        },
        "policy": policy_payload()["policy"],
    }


def policy_payload() -> Dict[str, Any]:
    return {
        "ok": True,
        "policy": {
            "cpu_ram_only": True,
            "gpu": "untouched",
            "ollama_num_gpu": os.environ.get("OLLAMA_NUM_GPU", "0"),
            "cuda_visible_devices": os.environ.get("CUDA_VISIBLE_DEVICES", ""),
            "ads": "forbidden",
            "tracking": "forbidden",
            "sponsors": "forbidden",
            "paid_recommendations": "forbidden",
            "data_sale": "forbidden",
            "external_sending": "disabled unless explicitly configured",
        },
    }


def manifest_payload() -> Dict[str, Any]:
    return {
        "ok": True,
        "version": "v2.14-root-identity-route-audit",
        "project": {
            "root": str(PROJECT_ROOT),
            "python": sys.version,
        },
        "modules": {
            "system": "base health and status",
            "chat": "local chat API",
            "memory": "local memory",
            "actions": "local actions",
            "models": "Ollama model routing",
            "autonomy": "doctor and tactical planning",
            "cloud": "official guarded cloud connectors",
            "knowledge": "open knowledge connectors",
            "compress": "token compression",
            "forge": "image/video/APK forge",
            "vision": "image analysis",
            "omnipresence": "Discord/Messenger/Mobile bridge",
            "omni_bridge": "mobile/omni replies and commands",
            "supervisor": "watchdog/snapshot/mobile home",
            "ezzio_identity": "root identity and route audit",
        },
        "important_urls": {
            "identity": "/ezzio/identity",
            "manifest": "/ezzio/manifest",
            "policy": "/ezzio/policy",
            "routes": "/ezzio/routes",
            "supervisor": "/supervisor/status",
            "watchdog": "/supervisor/watchdog",
            "mobile_home": "/supervisor/mobile-home",
            "truth": "/omni-bridge/truth",
            "commands": "/omni-bridge/commands",
        },
        "policy": policy_payload()["policy"],
    }


def routes_payload(app=None) -> Dict[str, Any]:
    routes = []

    if app is not None:
        for route in getattr(app, "routes", []):
            path = getattr(route, "path", "")
            name = getattr(route, "name", "")
            methods = sorted(getattr(route, "methods", []) or [])
            endpoint = getattr(route, "endpoint", None)
            endpoint_name = getattr(endpoint, "__name__", "") if endpoint else ""

            if path:
                routes.append(
                    {
                        "path": path,
                        "name": name,
                        "methods": methods,
                        "endpoint": endpoint_name,
                    }
                )

    routes.sort(key=lambda x: x["path"])

    duplicates = {}
    seen = {}
    for item in routes:
        key = item["path"]
        seen.setdefault(key, 0)
        seen[key] += 1

    for path, count in seen.items():
        if count > 1:
            duplicates[path] = count

    return {
        "ok": True,
        "count": len(routes),
        "duplicates": duplicates,
        "routes": routes,
    }
