"""Endpoints admin des modèles LLM : /api/models, /api/tools, etc."""
from fastapi import APIRouter
from typing import Any

router = APIRouter(prefix="/api", tags=["models"])

# NOTE : Ce fichier est un stub. Les endpoints /api/models et /api/tools
# sont encore dans web_server.py. Migrer progressivement.
# Exemple de migration :
#
# @router.get("/models")
# async def list_models() -> dict[str, Any]:
#     ...

@router.get("/_routes")
async def list_routes() -> dict[str, Any]:
    """Debug : liste les routes disponibles."""
    from web_server import app
    routes = [{"path": r.path, "methods": list(r.methods or [])} for r in app.routes if hasattr(r, "methods")]
    return {"count": len(routes), "routes": routes}