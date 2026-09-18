"""
Maintenance automatisée pour bases SQLite WAL et indexation FTS5 pour E-ZzIO.
Exécute les checkpoints WAL (TRUNCATE), l'optimisation des index et la purge.
"""

import logging
import sqlite3
from pathlib import Path

from ezzio.config import settings

logger = logging.getLogger("EzzioMemoryMaintenance")


def checkpoint_sqlite_db(db_path: Path | str, mode: str = "TRUNCATE") -> dict:
    """Exécute un checkpoint WAL et compacte la base SQLite."""
    target = Path(db_path)
    if not target.exists():
        return {"ok": False, "error": f"Base introuvable : {target}"}

    try:
        with sqlite3.connect(str(target)) as conn:
            cursor = conn.cursor()
            cursor.execute(f"PRAGMA wal_checkpoint({mode});")
            res = cursor.fetchone()

            # Optimisation des index SQLite
            cursor.execute("PRAGMA optimize;")

            # Optimisation FTS5 si existante
            try:
                cursor.execute("INSERT INTO session_messages_fts(session_messages_fts) VALUES('optimize');")
            except Exception:
                pass

            conn.commit()

        logger.info("[WAL-CHECKPOINT] Base %s compactée en mode %s (Busy: %s, Log: %s, Checkpointed: %s)", target.name, mode, res[0], res[1], res[2])
        return {
            "ok": True,
            "db": str(target),
            "busy": res[0],
            "log_frames": res[1],
            "checkpointed_frames": res[2]
        }
    except Exception as exc:
        logger.error("[WAL-CHECKPOINT-FAIL] Erreur sur %s : %s", target, exc)
        return {"ok": False, "db": str(target), "error": str(exc)}


def run_full_wal_maintenance() -> dict:
    """Exécute la maintenance complète sur toutes les bases actives du projet."""
    results = {}

    # 1. Base d'état E-ZzIO
    if settings.state_db_path.exists():
        results["ezzio_state"] = checkpoint_sqlite_db(settings.state_db_path, mode="TRUNCATE")

    # 2. Evidence Store
    evidence_db = settings.root_dir / "runtime" / "evidence" / "evidence.db"
    if evidence_db.exists():
        results["evidence_db"] = checkpoint_sqlite_db(evidence_db, mode="TRUNCATE")

    return results
