import os
from fastapi import FastAPI, HTTPException, Depends, Request
from fastapi.responses import HTMLResponse
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel
from dotenv import load_dotenv
from pathlib import Path

from runtime.telemetry.collector import TelemetryCollector
from runtime.recovery.queue.bus import RecoveryEventBus
from runtime.gateway import CognitiveRuntimeAdapter, get_system_health

ENV_PATH = Path(__file__).parent.parent.parent / "secrets" / ".env"
load_dotenv(dotenv_path=ENV_PATH)
SECRET_TOKEN = os.getenv("EZZIO_GATEWAY_SECRET", "ezzio-local-secure-token-2026")

app = FastAPI(title="E-ZZIO Autonomous Gateway", version="3.1.0")
security = HTTPBearer()

# Initialisation du Sous-Système Souverain
telemetry_collector = TelemetryCollector()
recovery_bus = RecoveryEventBus()
cognitive_adapter = CognitiveRuntimeAdapter(telemetry=telemetry_collector, recovery=recovery_bus)

class ChatRequest(BaseModel):
    user_id: str
    text: str
    speed: str = "auto"

def verify_token(credentials: HTTPAuthorizationCredentials = Depends(security)):
    if credentials.credentials != SECRET_TOKEN:
        raise HTTPException(status_code=403, detail="Invalid authorization token.")
    return credentials.credentials

@app.on_event("startup")
async def startup_event():
    telemetry_collector.start()
    recovery_bus.start()

@app.on_event("shutdown")
async def shutdown_event():
    telemetry_collector.stop()
    recovery_bus.stop()

@app.get("/", response_class=HTMLResponse)
async def dashboard():
    """Dashboard HTML minimaliste du Kernel E-zzio."""
    health = get_system_health(telemetry_collector, recovery_bus)
    telemetry_summary = telemetry_collector.get_summary() if telemetry_collector else {}
    
    html_content = f"""
    <html>
        <head>
            <title>E-ZZIO Kernel Dashboard</title>
            <style>
                body {{ background-color: #121212; color: #00ff00; font-family: monospace; padding: 20px; }}
                h1 {{ color: #00ffff; border-bottom: 1px solid #333; padding-bottom: 10px; }}
                .panel {{ border: 1px solid #333; padding: 15px; margin-bottom: 20px; border-radius: 5px; }}
                .status-ONLINE {{ color: #00ff00; font-weight: bold; }}
                .status-OFFLINE {{ color: #ff0000; font-weight: bold; }}
            </style>
        </head>
        <body>
            <h1>🧠 E-ZZIO AUTONOMOUS KERNEL</h1>
            <div class="panel">
                <h2>SYSTEM HEALTH</h2>
                <p>Status: <span class="status-{health['status']}">{health['status']}</span></p>
                <p>Memory: {health['memory']} | Recovery: {health['recovery']} | Mode: {health['hardware_mode']}</p>
            </div>
            <div class="panel">
                <h2>TELEMETRY SUBSYSTEM</h2>
                <p>Total Executions: {telemetry_summary.get('total_executions', 0)}</p>
                <p>Queue Backlog: {telemetry_summary.get('queue_backlog', 0)}</p>
                <p>Dropped Signals: {telemetry_summary.get('dropped_metrics', 0)}</p>
            </div>
        </body>
    </html>
    """
    return HTMLResponse(content=html_content)

@app.get("/health", dependencies=[Depends(verify_token)])
async def health_check():
    """Point d'entrée de santé pour le bot Discord."""
    return get_system_health(telemetry_collector, recovery_bus)

@app.post("/master/chat", dependencies=[Depends(verify_token)])
async def process_chat(request: ChatRequest):
    """Route les requêtes Discord vers le Cognitive Runtime Adapter."""
    try:
        response_text = await cognitive_adapter.process(user_id=request.user_id, message=request.text)
        return {"response": response_text}
    except Exception as e:
        raise HTTPException(status_code=500, detail="Cognitive Runtime Error")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("interfaces.api.server:app", host="127.0.0.1", port=8000, reload=False)
