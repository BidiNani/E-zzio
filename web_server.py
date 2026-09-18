# ==============================================================================
# E-ZZIO — Production Web Server & Unified Governor Lifespan
# File: G:\AI\E-zzio\web_server.py
# ==============================================================================
import os
import sys
from contextlib import asynccontextmanager
from pathlib import Path

import uvicorn
from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from core.security.guardian import setup_guardian

# 1. Configuration stricte du Path AVANT les imports locaux
ROOT_PATH = Path(r"G:\AI\E-zzio")
if str(ROOT_PATH) not in sys.path:
    sys.path.insert(0, str(ROOT_PATH))

# 2. Imports locaux
from fastapi.responses import HTMLResponse

from routers.capabilities import router as capabilities_router
from routers.generators import router as generators_router
from routers.health import router as health_router
from routers.master import router as master_router
from routers.memory import router as memory_router
from routers.perception import router as perception_router
from routers.research import init_research_router
from routers.research import router as research_router
from routers.telemetry import AGENT_VIEW_HTML
from routers.telemetry import router as telemetry_router
from routers.webhook import router as webhook_router
from runtime.execution.worker_bootstrap import worker_manager
from runtime.routers.llm import router as llm_router
from runtime.routers.mobile import router as mobile_router


# 3. Cycle de vie et Gouvernance
@asynccontextmanager
async def lifespan(app: FastAPI):
    # setup_production_logging() # DÉSACTIVÉ POUR DEBUG
    from core.memory.instance import memory_gateway
    await memory_gateway.init()
    await init_research_router()
    worker_manager.initialize_pool()
    yield
    worker_manager.shutdown()


# 4. Initialisation de l'API
app = FastAPI(title="E-ZZIO Sovereign API", version="v2.6-autonomic-tactical-core", lifespan=lifespan)
setup_guardian(app)

# Desktop / Tauri / Mobile Capacitor — CORS adapté aux environnements locaux et mobiles
# [B2-FIX2] CORSMiddleware retiré — géré par Guardian

# ============================================================
# AUTH MIDDLEWARE — API key (X-API-Key)
# Inactif si EZZIO_API_KEY est vide OU si EZZIO_DISABLE_AUTH=1
# ============================================================
import os as _os
import uuid

from fastapi import Request

_EZZIO_API_KEY = _os.getenv("EZZIO_API_KEY", "")
_EZZIO_DISABLE_AUTH = _os.getenv("EZZIO_DISABLE_AUTH", "0") == "1"
_PROTECTED_PREFIXES = ("/master/", "/api/accounts/", "/api/models/select")
_PUBLIC_PATHS = {"/health", "/ping", "/metrics", "/api/_routes", "/", "/agent-view"}


@app.middleware("http")
async def api_key_middleware(request: Request, call_next):
    # Désactivé explicitement (tests, dev) ou clé non configurée
    if _EZZIO_DISABLE_AUTH or not _EZZIO_API_KEY:
        return await call_next(request)

    path = request.url.path

    if path in _PUBLIC_PATHS or path.startswith("/perception/"):
        return await call_next(request)

    if any(path.startswith(p) for p in _PROTECTED_PREFIXES):
        provided = request.headers.get("X-API-Key", "")
        if provided != _EZZIO_API_KEY:
            from fastapi.responses import JSONResponse
            return JSONResponse(
                status_code=401,
                content={"detail": "API key required. Set X-API-Key header."},
            )

    return await call_next(request)


    # Endpoints protégés : clé requise
    if any(path.startswith(p) for p in _PROTECTED_PREFIXES):
        if not _EZZIO_API_KEY:
            # Clé non configurée → dev local, on laisse passer
            return await call_next(request)
        provided = request.headers.get("X-API-Key", "")
        if provided != _EZZIO_API_KEY:
            from fastapi.responses import JSONResponse
            return JSONResponse(
                status_code=401,
                content={"detail": "API key required. Set X-API-Key header."},
            )

    return await call_next(request)

@app.middleware("http")
async def correlation_id_middleware(request: Request, call_next):
    corr_id = request.headers.get("X-Correlation-ID", f"req_{uuid.uuid4().hex[:12]}")
    request.state.correlation_id = corr_id
    response = await call_next(request)
    response.headers["X-Correlation-ID"] = corr_id
    return response


# ============================================================
# E-ZZIO API Router (missions, approvals, files, etc.)
# ============================================================
from core.api.endpoints import router as ezzio_router

app.include_router(ezzio_router)




@app.get("/perception/status")
async def get_perception_status():
    return {
        "ok": True,
        "status": "ONLINE",
        "capabilities": [
            "universal_file_reader",
            "pdf_extraction",
            "code_symbol_map",
            "multimodal_vision"
        ]
    }


# 5. Injection des routeurs (sans doubler le préfixe pour le master)
app.include_router(llm_router)
app.include_router(mobile_router)
app.include_router(master_router)
app.include_router(health_router)
app.include_router(telemetry_router)
app.include_router(memory_router)
app.include_router(perception_router)
app.include_router(generators_router)
app.include_router(capabilities_router)
app.include_router(research_router)
from routers.accounts import router as accounts_router
from routers.models_admin import router as models_admin_router
from routers.search import router as search_router

app.include_router(webhook_router)
app.include_router(search_router)
app.include_router(accounts_router)
app.include_router(models_admin_router)


@app.get("/agent-view", response_class=HTMLResponse, include_in_schema=False)
async def agent_view_root():
    return AGENT_VIEW_HTML

# 6. Montage des fichiers statiques locaux (offline-first UI, CSS, assets)
web_static_dir = ROOT_PATH / "runtime" / "web"
if web_static_dir.exists():
    app.mount("/static", StaticFiles(directory=str(web_static_dir)), name="static")




@app.get("/")
async def get_dashboard():
    return FileResponse(r"G:\AI\E-zzio\runtime\web\index.html")


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("web_server:app", host=__import__("core.config", fromlist=["HOST"]).HOST, port=8001, log_level="info", access_log=False)


# ============================================================
# ENDPOINTS MODÈLES — Sélection dynamique (ajouté 2026-09-17)
# ============================================================

from core.config.active_model import get_active_model, set_active_model

# Catalogue des modèles Gemini valides au 17/09/2026
GEMINI_MODELS_CATALOG = [
    {"id": "gemini-3.8-flash",      "name": "Gemini 3.8 Flash",      "tier": "current",    "quality": 83, "desc": "Dernier flagship Flash"},
    {"id": "gemini-3.7-flash",      "name": "Gemini 3.7 Flash",      "tier": "superseded", "quality": 80, "desc": "Version précédente stable"},
    {"id": "gemini-3.6-flash",      "name": "Gemini 3.6 Flash",      "tier": "superseded", "quality": 75, "desc": "Ancien flagship stable"},
    {"id": "gemini-3.5-flash",      "name": "Gemini 3.5 Flash",      "tier": "stable",     "quality": 74, "desc": "Compromis vitesse/qualité"},
    {"id": "gemini-3.5-flash-lite", "name": "Gemini 3.5 Flash-Lite", "tier": "current",    "quality": 49, "desc": "Léger · 500 req/jour"},
    {"id": "gemini-3.1-flash-lite", "name": "Gemini 3.1 Flash-Lite", "tier": "stable",     "quality": 45, "desc": "Ancien Flash-Lite"},
]

@app.get("/api/models")
async def list_models():
    """
    Liste tous les modèles disponibles, groupés par clé API.
    Utilise la découverte dynamique existante (core/models/discovery/).
    """
    from core.models.discovery.gemini import GeminiDiscovery
    from core.models.discovery.groq import GroqDiscovery
    from core.models.discovery.ollama import OllamaDiscovery
    from core.models.discovery.openrouter import OpenRouterDiscovery
    from core.models.gemini_pool import gemini_pool

    active = get_active_model()

    # --- 1. Découverte Ollama (local) ---
    ollama_models = []
    try:
        ollama_disc = OllamaDiscovery()
        ollama_models = await ollama_disc.discover("http://localhost:11434")
    except Exception as e:
        print(f"[api/models] Ollama discovery erreur: {e}")

    # --- 1b. Découverte Groq ---
    groq_models = []
    try:
        groq_disc = GroqDiscovery()
        groq_models = await groq_disc.discover()
    except Exception as e:
        print(f"[api/models] Groq discovery erreur: {e}")

    # --- 1c. Découverte OpenRouter ---
    openrouter_models = []
    try:
        or_disc = OpenRouterDiscovery()
        openrouter_models = await or_disc.discover()
    except Exception as e:
        print(f"[api/models] OpenRouter discovery erreur: {e}")

    # --- 2. Découverte Gemini par clé (via le pool) ---
    gemini_by_key = {}
    try:
        # Récupérer les clés depuis le pool (projects[].keys[])
        discovery = GeminiDiscovery()
        key_index = 0

        for project in gemini_pool.projects:
            project_id = getattr(project, "project_id", f"project_{key_index}")
            project_keys = getattr(project, "keys", [])

            for slot in project_keys:
                key_index += 1
                key_str = getattr(slot, "key", None) or getattr(slot, "api_key", None)
                key_id = f"{project_id}_KEY_{key_index}"

                if not key_str:
                    gemini_by_key[key_id] = []
                    continue

                if not getattr(slot, "is_valid", True):
                    gemini_by_key[key_id] = []
                    print(f"[api/models] {key_id} invalidée, skip")
                    continue

                try:
                    models = await discovery.discover(key_str)
                    gemini_by_key[key_id] = models
                except Exception as e:
                    gemini_by_key[key_id] = []
                    print(f"[api/models] Gemini {key_id} discovery erreur: {e}")
    except Exception as e:
        print(f"[api/models] Pool accès erreur: {e}")

    # --- 3. Union des modèles Gemini (dédupliqués) ---
    gemini_union = {}
    for key_id, models in gemini_by_key.items():
        for m in models:
            mid = m["model_id"]
            if mid not in gemini_union:
                gemini_union[mid] = {**m, "available_keys": [key_id]}
            else:
                gemini_union[mid]["available_keys"].append(key_id)

    # --- 4. Retour structuré ---
    return {
        "active": active,
        "gemini": list(gemini_union.values()),
        "gemini_by_key": gemini_by_key,
        "ollama": ollama_models,
        "groq": groq_models,
        "openrouter": openrouter_models,
        "pool_status": {
            "keys_count": len(gemini_by_key),
            "models_count": len(gemini_union),
        }
    }

@app.post("/api/models/select")
async def select_model(payload: dict):
    """Change le modèle actif."""
    provider = payload.get("provider", "gemini")
    model_id = payload.get("model_id")
    if not model_id:
        return {"ok": False, "error": "model_id requis"}

    display = model_id
    for m in GEMINI_MODELS_CATALOG:
        if m["id"] == model_id:
            display = m["name"]
            break

    active = set_active_model(provider, model_id, display)
    return {"ok": True, "active": active}


@app.get("/api/tools")
async def list_tools():
    """
    Liste tous les outils de recherche disponibles (Tavily, Jina, ...).
    Affiche leur statut : clé configurée, actif/inactif.
    """
    import os

    from core.secrets import load_secrets

    load_secrets()

    def _check_key(key_name: str) -> bool:
        v = os.getenv(key_name)
        return bool(v and v.strip())

    tools = [
        {
            "id": "tavily",
            "name": "Tavily",
            "category": "search",
            "description": "Recherche web IA optimisée pour les LLM",
            "key_configured": _check_key("TAVILY_API_KEY"),
            "enabled": _check_key("TAVILY_API_KEY"),
            "url": "https://tavily.com",
        },
        {
            "id": "jina",
            "name": "Jina AI",
            "category": "search",
            "description": "Scraping et lecture web structurée",
            "key_configured": _check_key("JINA_API_KEY"),
            "enabled": _check_key("JINA_API_KEY"),
            "url": "https://jina.ai",
        },
        {
            "id": "searxng",
            "name": "SearxNG",
            "category": "search",
            "description": "Méta-moteur privé (self-hosted)",
            "key_configured": _check_key("SEARXNG_URL"),
            "enabled": False,
            "url": "https://searxng.github.io",
        },
    ]

    return {
        "tools": tools,
        "summary": {
            "total": len(tools),
            "enabled": sum(1 for t in tools if t["enabled"]),
        }
    }





@app.get("/api/models/registry")
async def list_models_registry():
    """
    Liste tous les modèles depuis le registre central (data/models/registry.json)
    + état des clés par provider (KeyPoolManager).
    """
    import json
    from pathlib import Path

    from core.models.key_pool import KeyPoolManager

    # 1. Charger le registre
    registry_path = Path("G:/AI/E-zzio/data/models/registry.json")
    registry_models = {}
    if registry_path.exists():
        with open(registry_path, encoding="utf-8") as f:
            data = json.load(f)
            registry_models = data.get("models", {})

    # 2. État du pool
    pool = KeyPoolManager()
    pool_status = {}
    for provider in pool.providers():
        slots = pool.available_slots(provider)
        pool_status[provider] = {
            "available_keys": len(slots),
            "total_keys": len(pool._slots.get(provider, [])),
        }

    # 3. Croiser : grouper par provider
    by_provider = {}
    for model_key, model_data in registry_models.items():
        provider = model_data.get("provider", "unknown")
        model_id = model_data.get("model_id", model_key)
        meta = model_data.get("metadata", {})

        if provider not in by_provider:
            by_provider[provider] = []

        by_provider[provider].append({
            "model_id": model_id,
            "display_name": meta.get("display_name", model_id),
            "context_window": model_data.get("context_window"),
            "max_output_tokens": model_data.get("max_output_tokens"),
            "supports_chat": model_data.get("supports_chat", True),
            "supports_tools": model_data.get("supports_tools", False),
            "supports_reasoning": model_data.get("supports_reasoning", False),
            "lifecycle": model_data.get("lifecycle", "UNKNOWN"),
            "tier": model_data.get("tier", "UNQUALIFIED"),
        })

    # 4. Ajouter Ollama (local)
    ollama_models = []
    try:
        import httpx
        async with httpx.AsyncClient(timeout=3.0) as client:
            r = await client.get("http://localhost:11434/api/tags")
            if r.status_code == 200:
                for m in r.json().get("models", []):
                    ollama_models.append({
                        "model_id": m["name"],
                        "display_name": m["name"],
                        "provider": "ollama",
                        "size": m.get("size"),
                    })
    except Exception:
        pass
    by_provider["ollama"] = ollama_models

    return {
        "ok": True,
        "by_provider": by_provider,
        "pool_status": pool_status,
        "total_models": sum(len(v) for v in by_provider.values()),
    }