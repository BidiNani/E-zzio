from fastapi import FastAPI
from routers.research import router as research_router
from core.evidence_store import EvidenceStore

app = FastAPI(
    title="E-ZZIO Autonomous Gateway",
    version="3.1.0",
    description="Interface souveraine de contrôle et d'orchestration cognitive"
)

# Enregistrement du routeur de recherche et d'intelligence
app.include_router(research_router)

@app.on_event("startup")
async def startup_event():
    evidence_store = EvidenceStore("runtime/evidence/evidence.db")
    await evidence_store.init()

@app.get("/")
async def root():
    return {"status": "online", "system": "E-ZZIO Core Microkernel", "version": "3.1.0"}

@app.get("/health")
async def health_check():
    return {"status": "healthy", "service": "ezzio-core"}
