"""app.py - Point d'entrée principal du serveur E-ZzIO pour Brave et API."""

from __future__ import annotations

from pathlib import Path
import uvicorn
from fastapi import HTTPException
from fastapi.responses import FileResponse

from core.api import create_app
from core.bus import EventBus
from core.cognitive_router import ModelRouter
from core.sandbox import SecuritySandbox

BASE_DIR = Path(__file__).resolve().parent
STATIC_DIR = BASE_DIR / "static"

# Instanciation de l'infrastructure persistante et sécurisée
bus = EventBus(db_path=BASE_DIR / "ezzio.db")
router = ModelRouter()
sandbox = SecuritySandbox(workspace_root=BASE_DIR)

app = create_app(bus=bus, router=router, sandbox=sandbox)


@app.get("/", response_class=FileResponse)
async def serve_desktop_ui() -> FileResponse:
    """Sert l'interface bureau unifiée E-ZzIO."""
    index_file = STATIC_DIR / "index.html"
    if not index_file.exists():
        raise HTTPException(status_code=404, detail="Interface introuvable.")
    return FileResponse(index_file)


if __name__ == "__main__":
    print("\n=======================================================")
    print("🚀 E-ZZIO UNIVERSAL DESKTOP DÉMARRÉ")
    print("🌐 Ouvrez Brave sur : http://127.0.0.1:8000")
    print("=======================================================\n")
    uvicorn.run(app, host="127.0.0.1", port=8000, log_level="info")
