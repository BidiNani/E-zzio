from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import importlib

app = FastAPI(title="E-ZZIO API", version="v2.9-indispensable-core")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

OPTIONAL_ROUTERS = [
    ("routers.system", "router"),
    ("routers.chat", "router"),
    ("routers.memory", "router"),
    ("routers.actions", "router"),
    ("routers.models", "router"),
    ("routers.autonomy", "router"),
    ("routers.cloud", "router"),
    ("routers.knowledge", "router"),
    ("routers.compress", "router"),
    ("routers.forge", "router"),
    ("routers.vision", "router"),
]

loaded_routers = []
failed_routers = []

for module_name, router_name in OPTIONAL_ROUTERS:
    try:
        module = importlib.import_module(module_name)
        router = getattr(module, router_name)
        app.include_router(router)
        loaded_routers.append(module_name)
    except Exception as exc:
        failed_routers.append({
            "module": module_name,
            "error": str(exc),
        })

@app.get("/router-status")
async def router_status():
    return {
        "loaded": loaded_routers,
        "failed": failed_routers,
    }
