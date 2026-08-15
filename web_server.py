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

# 1. Configuration stricte du Path AVANT les imports locaux
ROOT_PATH = Path(r"G:\AI\E-zzio")
if str(ROOT_PATH) not in sys.path:
    sys.path.insert(0, str(ROOT_PATH))

# 2. Imports locaux
from core.runtime.log_rotator import setup_production_logging
from runtime.execution.worker_bootstrap import worker_manager
from runtime.routers.llm import router as llm_router
from runtime.routers.mobile import router as mobile_router
from routers.master import router as master_router

# 3. Cycle de vie et Gouvernance
@asynccontextmanager
async def lifespan(app: FastAPI):
    # setup_production_logging() # DÉSACTIVÉ POUR DEBUG
    worker_manager.initialize_pool()
    yield
    worker_manager.shutdown()

# 4. Initialisation de l'API
app = FastAPI(title="E-ZZIO Sovereign API", version="v2.6-autonomic-tactical-core", lifespan=lifespan)

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
            "active_workers": worker_manager.max_workers
        }
    }

# 5. Injection des routeurs (sans doubler le préfixe pour le master)
app.include_router(llm_router)
app.include_router(mobile_router)
app.include_router(master_router)

@app.get('/')
async def get_dashboard():
    return FileResponse(r"G:\AI\E-zzio\runtime\web\index.html")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("web_server:app", host="127.0.0.1", port=8001, log_level="info")