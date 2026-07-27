from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import uvicorn
import asyncio

# Importation du noyau E-zzio (à lier avec ton orchestrateur réel)
from runtime.telemetry.collector import TelemetryCollector
from runtime.telemetry.metrics import ExecutionMetric

app = FastAPI(title="E-ZZIO Master Brain", version="3.0.0")
collector = TelemetryCollector()

class ChatRequest(BaseModel):
    user_id: str
    text: str
    speed: str = "auto"

@app.on_event("startup")
async def startup_event():
    collector.start()

@app.on_event("shutdown")
async def shutdown_event():
    collector.stop()

@app.post("/master/chat")
async def process_chat(request: ChatRequest):
    """Point d'entrée principal attendu par le Bot Discord."""
    try:
        # Télémétrie de l'entrée réseau
        collector.record_execution(ExecutionMetric(
            exec_id=f"req_{request.user_id}",
            action_name="discord_chat_input",
            status="RUNNING",
            duration_ms=0.0,
            cost=0.0,
            risk_level="LOW"
        ))
        
        # TODO: Remplacer par l'appel réel au Cognitive Runtime (Agent ReAct / Memory)
        await asyncio.sleep(1) # Simulation de traitement
        response_text = f"⚙️ [Noyau E-zzio Actif] Message reçu de {request.user_id}: '{request.text}'. Le cerveau cognitif est en cours de branchement."
        
        return {"response": response_text}
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    uvicorn.run("interfaces.api.server:app", host="127.0.0.1", port=8000, reload=False)
