import os, json, traceback
from fastapi import FastAPI
from pydantic import BaseModel
from typing import Optional
from pathlib import Path

# Utilisation du cerveau organique
from core.dispatcher import ezzio_dispatcher

BASE_DIR = Path(__file__).parent.resolve()
MEMORY_DIR = BASE_DIR / "memory"
WORKSPACE_DIR = BASE_DIR / "workspace"
MEMORY_DIR.mkdir(parents=True, exist_ok=True)
WORKSPACE_DIR.mkdir(parents=True, exist_ok=True)

app = FastAPI(title="E-zzio Organic Core Brain")

class ChatRequest(BaseModel):
    user_id: str
    text: str
    image_url: Optional[str] = None
    speed: str = "auto"

@app.post("/master/chat")
async def master_chat(request: ChatRequest):
    try:
        result = await ezzio_dispatcher.route_detailed_async(request.text, speed=request.speed)
        final_text = result.get("response", "")
        
        # Fallback de sécurité au niveau du cerveau
        if not final_text or not final_text.strip():
            final_text = "*(Je suis là, mais le modèle Ollama a retourné une réponse vide.)*"
            
        return {"response": final_text, "status": "success"}
    except Exception as e:
        print(f"❌ ERREUR CRITIQUE :\n{traceback.format_exc()}")
        return {"response": f"❌ Erreur interne du cerveau : {str(e)}", "status": "error"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8000)