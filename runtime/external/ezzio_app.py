"""E-ZZIO External Runtime — Unified Sovereign Bridge via CognitiveGateway."""
from __future__ import annotations
import logging
import traceback
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from core.cognition.cognitive_gateway import CognitiveGateway

app = FastAPI(title="E-ZZIO External Runtime Bridge")
gateway = CognitiveGateway(backend="cloud_gemini")

class ChatRequest(BaseModel):
    text: str
    session_id: str | None = "default"
    force_cloud: bool | None = True
    speed: str | None = "fast"
    image_url: str | None = None

@app.get("/health")
async def health_check():
    return {"status": "healthy", "ok": True}

@app.post("/master/chat")
async def master_chat(req: ChatRequest):
    try:
        # Routage souverain avec injection automatique de CanonicalIdentity
        target_backend = "cloud_gemini" if req.force_cloud else "local_primary"
        result = gateway.ask(
            task=req.text,
            backend=target_backend,
            context_payload={"force_cloud": req.force_cloud}
        )
        
        if result.get("status") == "ACCEPTED":
            return {
                "response": result.get("result", ""),
                "ok": True
            }
        else:
            raise HTTPException(
                status_code=500,
                detail=result.get("error", "Échec d'inférence cognitive")
            )
    except Exception as exc:
        print("\n--- [E-ZZIO ERREUR INTERNE CAPTURÉE] ---")
        traceback.print_exc()
        print("------------------------------------------\n")
        raise HTTPException(status_code=500, detail=str(exc))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8001)
