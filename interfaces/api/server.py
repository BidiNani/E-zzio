from fastapi import FastAPI
from routers.research import router as research_router
from routers.chat import router as chat_router
from core.memory.unified_gateway import UnifiedMemoryGateway

app = FastAPI(
    title="E-ZZIO Autonomous Gateway",
    version="3.2.0",
    description="Interface souveraine de contrôle et d'orchestration cognitive"
)

# Montage des routeurs
app.include_router(research_router)
app.include_router(chat_router)

@app.on_event("startup")
async def startup_event():
    mem = UnifiedMemoryGateway("runtime/evidence/evidence.db")
    await mem.init()

@app.get("/")
async def root():
    return {"status": "online", "system": "E-ZZIO Core Microkernel", "version": "3.2.0"}

@app.get("/health")
async def health_check():
    return {"status": "healthy", "service": "ezzio-core"}
