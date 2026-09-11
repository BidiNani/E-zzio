"""
Passerelle API REST & Streaming SSE asynchrone pour E-ZzIO.
"""

import json
import logging
from typing import AsyncGenerator
from pathlib import Path
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse, HTMLResponse

from ezzio.config import settings
from ezzio.schemas import ChatRequest, ChatResponse, HealthStatus
from ezzio.graph.workflow import app as graph_app
from ezzio.rag.engine import get_rag_engine
from ezzio.tools.file_tools import list_project_files
from ezzio.tools.system_tools import check_ollama_health
from ezzio.self_repair.codebase_catalog import get_codebase_catalog
from ezzio.self_repair.auto_healer import AutoHealer

logger = logging.getLogger("EzzioAPI")

from contextlib import asynccontextmanager
from ezzio.memory.maintenance import run_full_wal_maintenance


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Cycle de vie de l'application : initialisation et compactage WAL à l'arrêt."""
    logger.info("[STARTUP] Démarrage de la passerelle E-ZzIO.")
    yield
    logger.info("[SHUTDOWN] Exécution du compactage WAL et optimisation SQLite...")
    try:
        maintenance_res = run_full_wal_maintenance()
        logger.info("[SHUTDOWN] Résultat maintenance WAL : %s", maintenance_res)
    except Exception as exc:
        logger.error("[SHUTDOWN-ERROR] Échec compactage WAL : %s", exc)


UI_FILE = Path(__file__).resolve().parent / "ui" / "index.html"

app = FastAPI(
    title="E-ZzIO Core API Gateway",
    version="2.0.0",
    description="Interface REST & Streaming SSE pour l'orchestrateur autonome et le moteur RAG E-ZzIO.",
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

# Inclusion du Noyau Forge & Perception Universelle
try:
    from routers.forge import router as forge_router
    app.include_router(forge_router)
    logger.info("Noyau Forge /forge monté avec succès.")
except Exception as forge_err:
    logger.warning("Noyau Forge non disponible : %s", forge_err)

try:
    from routers.perception import router as perception_router
    app.include_router(perception_router)
    logger.info("Couche Perception Universelle /perception montée avec succès.")
except Exception as p_err:
    logger.warning("Couche Perception non disponible : %s", p_err)

try:
    from routers.vision import router as vision_router
    app.include_router(vision_router)
    logger.info("Module Vision /vision monté avec succès.")
except Exception as v_err:
    logger.warning("Module Vision non disponible : %s", v_err)


@app.get("/", response_class=HTMLResponse)
async def root_ui():
    """Interface utilisateur Web E-ZzIO Neural Control."""
    if UI_FILE.exists():
        return HTMLResponse(content=UI_FILE.read_text(encoding="utf-8"))
    return HTMLResponse(content="<h1>E-ZzIO API Gateway Online</h1><p>UI file not found. Visit <a href='/docs'>/docs</a></p>")


@app.get("/api/info")
async def api_info():
    """Informations de découverte de l'API E-ZzIO."""
    return {
        "status": "online",
        "service": "E-ZzIO Autonomous Core",
        "version": "2.0.0",
        "endpoints": {
            "ui": "/",
            "chat": "/api/chat",
            "chat_stream": "/api/chat/stream",
            "health": "/api/health",
            "catalog": "/api/catalog",
            "heal": "/api/heal",
            "ingest": "/api/ingest",
            "files": "/api/files",
            "docs": "/docs"
        }
    }


@app.post("/api/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    """Exécute une requête complète via le graphe LangGraph avec persistance de session par thread_id."""
    initial_state = {
        "query": request.query,
        "thread_id": request.thread_id,
        "route": "direct",
        "answer": "",
        "sources": [],
        "model_used": "",
    }
    
    config = {"configurable": {"thread_id": request.thread_id}}
    
    try:
        final_state = await graph_app.ainvoke(initial_state, config=config)
        return ChatResponse(
            query=request.query,
            thread_id=request.thread_id,
            route=final_state.get("route", "direct"),
            model_used=final_state.get("model_used", "unknown"),
            answer=final_state.get("answer", ""),
            sources=final_state.get("sources", []),
        )
    except Exception as exc:
        logger.error("Erreur lors de l'exécution du graphe : %s", exc, exc_info=True)
        raise HTTPException(status_code=500, detail=str(exc))


async def event_generator(query: str, thread_id: str) -> AsyncGenerator[str, None]:
    """Générateur SSE pour streamer les événements et la réponse en temps réel token-par-token."""
    yield f"data: {json.dumps({'event': 'status', 'message': 'Connexion neuronale à Gemini Flash...'})}\n\n"
    
    try:
        from ezzio.llm.client import get_llm_client
        from ezzio.memory.context_window import get_context_manager
        
        ctx_mgr = get_context_manager()
        history = ctx_mgr.get_pruned_context(thread_id)
        
        # Contexte léger (derniers 4 échanges)
        context_blocks = []
        for msg in history[-4:]:
            role = "Utilisateur" if msg["role"] == "user" else "Assistant"
            context_blocks.append(f"{role}: {msg['content']}")
            
        history_str = "\n".join(context_blocks)
        full_prompt = f"Historique récent :\n{history_str}\n\nNouvelle question : {query}" if history_str else query
        
        try:
            from core.cloud_brain_broker import build_system_prompt
            system_prompt = build_system_prompt()
        except Exception:
            system_prompt = "Tu es E-ZZIO, âme numérique souveraine et assistant technique d'élite conçu par BidiNani."

        yield f"data: {json.dumps({'event': 'route', 'route': 'direct', 'model': f'{settings.cloud_model_primary} (Streaming SSE)'})}\n\n"
        
        llm = get_llm_client()
        full_answer = []
        
        async for token in llm.astream(prompt=full_prompt, system_prompt=system_prompt):
            full_answer.append(token)
            yield f"data: {json.dumps({'event': 'token', 'chunk': token})}\n\n"
            
        final_text = "".join(full_answer)
        
        # Sauvegarde mémorielle
        ctx_mgr.add_message(thread_id, "user", query)
        ctx_mgr.add_message(thread_id, "assistant", final_text)
        
        yield f"data: {json.dumps({'event': 'done', 'sources': []})}\n\n"
    except Exception as exc:
        logger.error("Erreur SSE : %s", exc, exc_info=True)
        yield f"data: {json.dumps({'event': 'error', 'message': str(exc)})}\n\n"


@app.post("/api/chat/stream")
async def chat_stream(request: ChatRequest):
    """Point de terminaison SSE pour recevoir la réponse en temps réel token-par-token."""
    return StreamingResponse(
        event_generator(request.query, request.thread_id),
        media_type="text/event-stream"
    )


@app.get("/api/health", response_model=HealthStatus)
async def health():
    """Contrôle de santé du serveur, des modèles Ollama et de ChromaDB."""
    return await check_ollama_health()


@app.get("/api/catalog")
async def get_catalog():
    """Renvoie le catalogue universel d'auto-connaissance du codebase."""
    catalog = get_codebase_catalog()
    return catalog.load()


@app.post("/api/heal")
async def run_heal():
    """Lance un diagnostic et l'auto-guérison du code source."""
    healer = AutoHealer()
    return healer.diagnose_all()


@app.post("/api/ingest")
async def run_ingest():
    """Déclenche la réindexation vectorielle RAG de la documentation et du code."""
    engine = get_rag_engine()
    count = engine.ingest_codebase()
    return {"status": "success", "indexed_chunks": count}


@app.get("/api/files")
async def list_files():
    """Liste tous les fichiers surveillés par E-ZzIO."""
    files = list_project_files()
    return {"total": len(files), "files": files}


@app.post("/api/memory/checkpoint")
async def memory_checkpoint():
    """Déclenche la maintenance immédiate et le compactage WAL de la mémoire."""
    return run_full_wal_maintenance()
