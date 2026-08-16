import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from routers.chat import router as chat_router, init_chat_router
from routers.research import router as research_router, init_research_router

logger = logging.getLogger("ezzio.api.server")

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Gestionnaire de cycle de vie moderne FastAPI (Startup & Shutdown)."""
    logger.info("[*] Démarrage du micro-noyau E-ZZIO API...")
    await init_chat_router()
    await init_research_router()
    logger.info("[OK] Tous les sous-systèmes API sont initialisés et prêts.")
    yield
    logger.info("[*] Arrêt propre de l'API E-ZZIO.")

app = FastAPI(
    title="E-ZZIO OS API",
    description="Passerelle API souveraine locale et cloud gouvernée",
    version="1.0.0",
    lifespan=lifespan
)

# Configuration CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Enregistrement des routes
app.include_router(chat_router)
app.include_router(research_router)

@app.get("/health", tags=["System"])
async def health_check():
    return {"status": "healthy", "service": "ezzio-core"}
