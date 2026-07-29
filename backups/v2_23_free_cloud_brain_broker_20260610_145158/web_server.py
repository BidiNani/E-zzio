from __future__ import annotations

import importlib
import os
import sys
import traceback
from pathlib import Path
from typing import Any

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

PROJECT_ROOT = Path("G:/AI/E-zzio")

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

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
    "EZZIO_OLLAMA_THREADS_FAST": "8",
    "EZZIO_OLLAMA_THREADS_NORMAL": "12",
    "EZZIO_OLLAMA_THREADS_DEEP": "16",
}

for key, value in CPU_ONLY_ENV.items():
    os.environ[key] = value

app = FastAPI(
    title="E-ZZIO",
    version="v2.22-pc-commander",
    description="E-ZZIO local CPU/RAM-only assistant. PC Commander, safe action queue, human chat truth guard, memory, human loop, clean core, maintenance, no ads.",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://127.0.0.1:5173",
        "http://localhost:5173",
        "http://127.0.0.1:3000",
        "http://localhost:3000",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

router_load_report: dict[str, Any] = {
    "loaded": [],
    "failed": {},
}

@app.get("/")
async def root():
    return {
        "ok": True,
        "name": "E-ZZIO",
        "version": "v2.22-pc-commander",
        "project_root": str(PROJECT_ROOT),
        "features": {
            "brain": "/brain/status",
            "brain_gateway": "/api/brain/status",
            "pc_chat": "/api/chat/pc",
            "router_chat": "/api/chat/router",
            "human": "/human/status",
            "human_chat": "/human-chat/status",
            "safe_actions": "/safe-actions/status",
            "commander": "/commander/status",
            "commander_chat": "/api/chat/commander",
            "safe_action_queue": "/safe-actions/queue",
            "human_chat_message": "/api/chat/human",
            "human_tick": "/human/tick",
            "human_journal": "/human/journal",
            "performance": "/performance/status",
            "maintenance": "/maintenance/status",
            "audit": "/maintenance/audit",
            "dust": "/maintenance/dust",
            "supervisor": "/supervisor/status",
            "watchdog": "/supervisor/watchdog",
        },
        "policy": {
            "cpu_ram_only": True,
            "gpu": "untouched",
            "ads": "forbidden",
            "tracking": "forbidden",
            "sponsors": "forbidden",
            "destructive_autonomy": "forbidden_without_confirmation",
        },
    }

@app.get("/status")
async def status():
    return {
        "ok": True,
        "name": "E-ZZIO",
        "version": "v2.22-pc-commander",
        "project_root": str(PROJECT_ROOT),
        "policy": {
            "cpu_ram_only": True,
            "ollama_num_gpu": os.environ.get("OLLAMA_NUM_GPU"),
            "cuda_visible_devices": os.environ.get("CUDA_VISIBLE_DEVICES"),
            "ezzio_gpu_policy": os.environ.get("EZZIO_GPU_POLICY"),
            "no_ads": os.environ.get("EZZIO_NO_ADS"),
            "no_tracking": os.environ.get("EZZIO_NO_TRACKING"),
            "no_sponsors": os.environ.get("EZZIO_NO_SPONSORS"),
        },
    }

@app.get("/router-status")
async def router_status():
    return {
        "ok": True,
        "version": "v2.22-pc-commander",
        "loaded_count": len(router_load_report["loaded"]),
        "failed_count": len(router_load_report["failed"]),
        "loaded": router_load_report["loaded"],
        "failed": router_load_report["failed"],
    }

@app.get("/no-ads-policy")
async def no_ads_policy():
    return {
        "ok": True,
        "policy": "E-ZZIO ne doit intégrer aucune publicité, aucun tracking publicitaire, aucun sponsor, aucune recommandation payée.",
        "details": {
            "ads": "forbidden",
            "tracking": "forbidden",
            "sponsors": "forbidden",
            "paid_recommendations": "forbidden",
            "data_sale": "forbidden",
        },
    }

ROUTER_MODULES = [
    "routers.ezzio_identity",
    "routers.system",
    "routers.chat",
    "routers.memory",
    "routers.actions",
    "routers.models",
    "routers.autonomy",
    "routers.cloud",
    "routers.knowledge",
    "routers.compress",
    "routers.forge",
    "routers.vision",
    "routers.omnipresence",
    "routers.omni_bridge",
    "routers.supervisor",
    "routers.performance",
    "routers.brain",
    "routers.brain_gateway",
    "routers.admin_maintenance",
    "routers.human_loop",
    "routers.human_chat",
    "routers.safe_actions",
    "routers.pc_commander",
]

def load_router(module_name: str) -> None:
    try:
        module = importlib.import_module(module_name)
        router = getattr(module, "router", None)

        if router is None:
            router_load_report["failed"][module_name] = "Aucun attribut router trouvé."
            return

        app.include_router(router)
        router_load_report["loaded"].append(module_name)

    except Exception as exc:
        router_load_report["failed"][module_name] = {
            "error": str(exc),
            "traceback": traceback.format_exc(limit=8),
        }

for module_name in ROUTER_MODULES:
    load_router(module_name)
