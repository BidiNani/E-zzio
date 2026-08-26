import sqlite3
import logging
from contextlib import contextmanager
from pathlib import Path
from typing import Generator

logger = logging.getLogger("ezzio.storage")


class StorageEngine:
    @staticmethod
    @contextmanager
    def get_connection(db_path: Path, timeout: float = 5.0) -> Generator[sqlite3.Connection, None, None]:
        """
        Fournit une connexion SQLite sécurisée avec les paramètres de production :
        - Mode WAL (Write-Ahead Logging)
        - Busy timeout de 5000ms
        - Contraintes de clés étrangères actives
        - Gestion automatique du commit/rollback via contexte
        """
        db_path = Path(db_path)
        db_path.parent.mkdir(parents=True, exist_ok=True)

        conn = sqlite3.connect(db_path, timeout=timeout, check_same_thread=False)
        try:
            conn.execute("PRAGMA journal_mode=WAL;")
            conn.execute("PRAGMA busy_timeout=5000;")
            conn.execute("PRAGMA foreign_keys=ON;")
            yield conn
            conn.commit()
        except Exception as e:
            conn.rollback()
            logger.error(f"[SQLITE ERROR] Transaction annulée sur {db_path.name} : {e}")
            raise
        finally:
            conn.close()


storage = StorageEngine()
