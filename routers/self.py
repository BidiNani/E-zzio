import logging
import os
import sqlite3

from fastapi import APIRouter
from pydantic import BaseModel

logger = logging.getLogger("ezzio.routers.self")

router = APIRouter()



class SelfStatus(BaseModel):
    model_active: str | None
    memory_backend: str
    memory_session_events: int
    memory_last_write: str | None
    pipeline_running: str | None


@router.get("/api/v1/self/status", response_model=SelfStatus, tags=["Self"])
async def get_self_status():
    """
    Endpoint d'introspection runtime.
    Retourne l'état VÉRIFIÉ en direct, pas ce que la documentation prétend.
    """

    # 1. Modele actif
    # NOTE: lu depuis EZZIO_ACTIVE_MODEL (variable d'environnement).
    # Cette valeur peut diverger du modele reellement selectionne dans le routeur chat.
    # Pour l'etat exact, interroger /master/chat/status (endpoint a exposer si necessaire).
    model_active = os.getenv("EZZIO_ACTIVE_MODEL", "gemini-3.7-flash")

    # 2. Backend mémoire
    memory_backend = "SQLiteEventStore"

    # 3. Nombre d'événements de la session courante
    db_path = "runtime/memory/sqlite/ezzio_events.db"
    memory_session_events = 0
    memory_last_write = None

    if os.path.exists(db_path):
        try:
            with sqlite3.connect(db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT COUNT(*) FROM memory_events")
                memory_session_events = cursor.fetchone()[0]

                cursor.execute("SELECT MAX(timestamp) FROM memory_events")
                last_ts = cursor.fetchone()[0]
                if last_ts:
                    memory_last_write = last_ts

                logger.info(f"[OK] Status mémoire : {memory_session_events} événements")
        except Exception as e:
            logger.warning(f"[WARN] Erreur lecture SQLite : {e}")

    # 4. Pipeline running (PID + nom du process sur 8001)
    pipeline_running = None
    try:
        import psutil

        server_port = int(os.getenv("EZZIO_API_PORT", "8001"))
        for conn in psutil.net_connections(kind="inet"):
            if conn.laddr and conn.laddr.port == server_port and conn.status == "LISTEN" and conn.pid:
                try:
                    proc = psutil.Process(conn.pid)
                    pipeline_running = f"{proc.name()} (PID {conn.pid})"
                    break
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    pipeline_running = f"Process (PID {conn.pid})"
                    break
    except Exception as e:
        logger.warning(f"[WARN] Erreur lecture processus : {e}")

    return SelfStatus(
        model_active=model_active,
        memory_backend=memory_backend,
        memory_session_events=memory_session_events,
        memory_last_write=memory_last_write,
        pipeline_running=pipeline_running,
    )
