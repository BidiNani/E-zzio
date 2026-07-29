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
}

for key, value in CPU_ONLY_ENV.items():
    os.environ[key] = value

app = FastAPI(
    title="E-ZZIO",
    version="v2.14-root-identity-route-audit",
    description="E-ZZIO local CPU/RAM-only assistant. No ads, no tracking, no sponsors.",
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
    from core.ezzio_identity import identity_payload
    return identity_payload()

@app.get("/status")
async def status():
    from core.ezzio_identity import identity_payload
    return identity_payload()

@app.get("/router-status")
async def router_status():
    return {
        "ok": True,
        "version": "v2.14-root-identity-route-audit",
        "loaded_count": len(router_load_report["loaded"]),
        "failed_count": len(router_load_report["failed"]),
        "loaded": router_load_report["loaded"],
        "failed": router_load_report["failed"],
    }

@app.get("/no-ads-policy")
async def no_ads_policy():
    from core.ezzio_identity import policy_payload
    policy = policy_payload()
    return {
        "ok": True,
        "policy": "E-ZZIO ne doit intégrer aucune publicité, aucun tracking publicitaire, aucun sponsor, aucune recommandation payée.",
        "details": policy["policy"],
        "allowed": [
            "connecteurs officiels configurés par Enrik",
            "webhooks explicites",
            "API publiques utiles",
            "logs locaux",
            "bridge mobile local",
        ],
        "forbidden": [
            "ads",
            "sponsored content",
            "tracking pixels",
            "profilage publicitaire",
            "vente de données",
            "modules de pub dans UI/API/mobile",
        ],
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
