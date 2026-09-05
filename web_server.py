# ==============================================================================
# E-ZZIO — Production Web Server & Unified Governor Lifespan
# File: G:\AI\E-zzio\web_server.py
# ==============================================================================
import os
import sys
import uvicorn
from pathlib import Path
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

# 1. Configuration stricte du Path AVANT les imports locaux
ROOT_PATH = Path(r"G:\AI\E-zzio")
if str(ROOT_PATH) not in sys.path:
    sys.path.insert(0, str(ROOT_PATH))

# 2. Imports locaux
from runtime.execution.worker_bootstrap import worker_manager
from runtime.routers.llm import router as llm_router
from runtime.routers.mobile import router as mobile_router
from routers.master import router as master_router
from routers.memory import router as memory_router


# 3. Cycle de vie et Gouvernance
@asynccontextmanager
async def lifespan(app: FastAPI):
    # setup_production_logging() # DÉSACTIVÉ POUR DEBUG
    from core.memory.instance import memory_gateway
    await memory_gateway.init()
    worker_manager.initialize_pool()
    yield
    worker_manager.shutdown()


# 4. Initialisation de l'API
app = FastAPI(title="E-ZZIO Sovereign API", version="v2.6-autonomic-tactical-core", lifespan=lifespan)

import uuid
from fastapi import Request


@app.middleware("http")
async def correlation_id_middleware(request: Request, call_next):
    corr_id = request.headers.get("X-Correlation-ID", f"req_{uuid.uuid4().hex[:12]}")
    request.state.correlation_id = corr_id
    response = await call_next(request)
    response.headers["X-Correlation-ID"] = corr_id
    return response


@app.get("/health")
async def health_check():
    return {
        "status": "ONLINE",
        "ok": True,
        "service": "E-ZZIO",
        "pid": os.getpid(),
        "worker_pool": {
            "status": worker_manager.status,
            "profile": worker_manager.profile_name,
            "max_ram_gb": worker_manager.max_ram_gb,
            "active_workers": worker_manager.max_workers,
        },
    }


@app.get("/metrics")
async def get_metrics():
    from core.models.provider_health import probe_ollama_status
    ollama_ok = probe_ollama_status()
    return {
        "ok": True,
        "circuit_breaker": "CLOSED",
        "providers_health": {
            "ollama_local": "ONLINE" if ollama_ok else "OFFLINE"
        }
    }


@app.get("/perception/status")
async def get_perception_status():
    return {
        "ok": True,
        "status": "ONLINE",
        "capabilities": [
            "universal_file_reader",
            "pdf_extraction",
            "code_symbol_map",
            "multimodal_vision"
        ]
    }


# 5. Injection des routeurs (sans doubler le préfixe pour le master)
app.include_router(llm_router)
app.include_router(mobile_router)
app.include_router(master_router)
app.include_router(memory_router)

# 6. Montage des fichiers statiques locaux (offline-first UI, CSS, assets)
web_static_dir = ROOT_PATH / "runtime" / "web"
if web_static_dir.exists():
    app.mount("/static", StaticFiles(directory=str(web_static_dir)), name="static")


@app.get("/")
async def get_dashboard():
    return FileResponse(r"G:\AI\E-zzio\runtime\web\index.html")


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("web_server:app", host="0.0.0.0", port=8001, log_level="info")
