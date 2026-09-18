"""
E-ZZIO V7.54 — Cognitive Memory Indexer (FTS5)
Module en lecture seule sur les sources. Construit un index de recherche lexicale rapide.
"""

import logging
import sqlite3
from datetime import UTC, datetime
from pathlib import Path

ROOT_DIR = Path(r"G:\AI\E-zzio")
INDEX_DB = ROOT_DIR / "runtime" / "cognitive" / "index" / "memory_index.sqlite"

logging.basicConfig(level=logging.INFO, format="[COGNITIVE INDEXER] %(message)s")


class CognitiveIndexer:
    def __init__(self):
        self.db_path = INDEX_DB
        self._initialize_database()

    def _initialize_database(self):
        """Initialise la table virtuelle FTS5 pour la recherche plein texte."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                # Table virtuelle FTS5. Optimisée pour la recherche sur 'content'
                cursor.execute("""
                    CREATE VIRTUAL TABLE IF NOT EXISTS memory_search USING fts5(
                        content,        # Le texte extrait (ex: "Exécution outil validée")
                        memory_type,    # Type: experience, audit, decision, profile
                        source_path,    # Fichier d'origine (ex: runtime/audit/event.jsonl)
                        source_hash,    # Hash SHA-256 du fichier d'origine ou de la ligne
                        confidence,     # Score de fiabilité (ex: 0.98)
                        importance,     # Score d'importance (1 à 10)
                        last_validated  # Date au format ISO
                    );
                """)
                conn.commit()
        except sqlite3.Error as e:
            logging.error(f"Erreur fatale lors de l'initialisation FTS5 : {e}")

    def insert_memory_node(self, content: str, memory_type: str, source_path: str, source_hash: str, confidence: float, importance: int):
        """Insère un nœud cognitif extrait des sources immuables."""
        timestamp = datetime.now(UTC).isoformat()
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute(
                    """
                    INSERT INTO memory_search (content, memory_type, source_path, source_hash, confidence, importance, last_validated)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                    (content, memory_type, source_path, source_hash, confidence, importance, timestamp),
                )
                conn.commit()
        except sqlite3.Error as e:
            logging.error(f"Échec de l'insertion du nœud : {e}")


if __name__ == "__main__":
    indexer = CognitiveIndexer()
    logging.info("Moteur d'indexation FTS5 prêt. En attente des extracteurs JSONL/MD/SQLite.")
