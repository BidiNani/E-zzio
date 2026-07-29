from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from core.dispatcher import ezzio_dispatcher
from core.memory import ezzio_memory
from core.actions import toolbox

app = FastAPI(title="E-ZZIO API", version="v2.2-pro-moe-fast")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

class Prompt(BaseModel):
    text: str

class MemoryQuery(BaseModel):
    query: str
    limit: int = 10

class CreateFileRequest(BaseModel):
    filename: str
    content: str

@app.get("/")
async def root_status():
    return {
        "name": "E-ZZIO",
        "version": "v2.2-pro-moe-fast",
        "status": "alive",
        "gpu_policy": "disabled_for_ezzio",
        "num_gpu": 0,
    }

@app.get("/status")
async def status():
    return ezzio_dispatcher.status()

@app.post("/route")
async def route(prompt: Prompt):
    key, organ, score, hits = ezzio_dispatcher.select_organ(prompt.text)
    return {
        "selected_organ": key,
        "organ_label": organ["label"],
        "emotion": organ["emotion"],
        "talent": organ["talent"],
        "model": organ["model"],
        "fallback": organ["fallback"],
        "score": score,
        "hits": hits,
        "gpu_policy": "disabled_for_ezzio",
        "num_gpu": 0,
    }

@app.post("/chat")
async def chat(prompt: Prompt):
    return ezzio_dispatcher.route_detailed(prompt.text)

@app.post("/api/chat")
async def api_chat(prompt: Prompt):
    return ezzio_dispatcher.route_detailed(prompt.text)

@app.get("/memory/recent")
async def memory_recent():
    return {"items": ezzio_memory.get_context(last_n=20)}

@app.post("/memory/search")
async def memory_search(query: MemoryQuery):
    return {"items": ezzio_memory.search(query.query, limit=query.limit)}

@app.post("/memory/compact")
async def memory_compact():
    return ezzio_memory.compact(keep_last=300)

@app.post("/actions/create_file")
async def create_file(req: CreateFileRequest):
    return {"result": toolbox.create_file(req.filename, req.content)}

@app.get("/actions/list_files")
async def list_files(path: str = "."):
    return {"result": toolbox.list_files(path)}

@app.get("/actions/status")
async def actions_status():
    return toolbox.status()
