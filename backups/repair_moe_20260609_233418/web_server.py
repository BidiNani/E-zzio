from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
# Assure-toi que ton import est correct ici
from core.dispatcher import ezzio_dispatcher

# 1. IL FAUT DÉFINIR APP AVANT DE L'UTILISER
app = FastAPI()

# 2. CONFIGURER LE MIDDLEWARE ENSUITE
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

class Prompt(BaseModel):
    text: str

# 3. ET SEULEMENT MAINTENANT UTILISER @app
@app.post("/chat")
async def chat(prompt: Prompt):
    response = ezzio_dispatcher.route(prompt.text)
    return {"response": response}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)