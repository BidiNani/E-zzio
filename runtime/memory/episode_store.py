import sqlite3
import json
from pathlib import Path
from typing import List, Optional
from runtime.memory.episode import Episode, EpisodeStep

class EpisodeStore:
    """Stocke et récupère les épisodes via une connexion persistante unique et un cycle de vie idempotent."""

    def __init__(self, db_path: Optional[str] = None):
        if db_path is None:
            db_path = Path("runtime/memory/sqlite/cognitive_store.db")
        else:
            db_path = Path(db_path) if str(db_path) != ":memory:" else ":memory:"
        
        if str(db_path) != ":memory:":
            db_path.parent.mkdir(parents=True, exist_ok=True)
            
        self.db_path = db_path
        self._connection = None
        self._closed = False
        self._init_db()

    def _get_connection(self) -> sqlite3.Connection:
        if self._closed:
            raise RuntimeError("EpisodeStore is already closed.")
        if self._connection is None:
            db_target = ":memory:" if str(self.db_path) == ":memory:" else str(self.db_path)
            self._connection = sqlite3.connect(db_target)
            self._connection.row_factory = sqlite3.Row
        return self._connection

    def _init_db(self):
        conn = self._get_connection()
        conn.execute("""
            CREATE TABLE IF NOT EXISTS episodes (
                episode_id TEXT PRIMARY KEY,
                session_id TEXT NOT NULL,
                trace_id TEXT NOT NULL,
                start_time TEXT NOT NULL,
                end_time TEXT NOT NULL,
                goal TEXT NOT NULL,
                steps_json TEXT NOT NULL,
                outcome TEXT NOT NULL,
                importance REAL NOT NULL,
                consolidated INTEGER NOT NULL
            )
        """)
        try:
            conn.execute("ALTER TABLE episodes ADD COLUMN trace_id TEXT DEFAULT 'unknown'")
        except sqlite3.OperationalError:
            pass
        conn.commit()

    def save_episode(self, episode: Episode):
        steps_data = [
            {
                "event_id": s.event_id,
                "event_type": s.event_type,
                "timestamp": s.timestamp,
                "payload": s.payload
            } for s in episode.steps
        ]
        conn = self._get_connection()
        conn.execute("""
            INSERT OR REPLACE INTO episodes 
            (episode_id, session_id, trace_id, start_time, end_time, goal, steps_json, outcome, importance, consolidated)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            episode.episode_id,
            episode.session_id,
            episode.trace_id,
            episode.start_time,
            episode.end_time,
            episode.goal,
            json.dumps(steps_data),
            episode.outcome,
            episode.importance,
            1 if episode.consolidated else 0
        ))
        conn.commit()

    def get_episodes_by_session(self, session_id: str) -> List[Episode]:
        conn = self._get_connection()
        cursor = conn.execute(
            "SELECT * FROM episodes WHERE session_id = ? ORDER BY start_time ASC",
            (session_id,)
        )
        rows = cursor.fetchall()
        return [self._row_to_episode(row) for row in rows]

    def close(self):
        """Fermeture propre et idempotente de la ressource."""
        if self._connection and not self._closed:
            try:
                self._connection.commit()
                self._connection.close()
            finally:
                self._connection = None
                self._closed = True

    def _row_to_episode(self, row: sqlite3.Row) -> Episode:
        steps_raw = json.loads(row["steps_json"])
        steps = [
            EpisodeStep(
                event_id=s["event_id"],
                event_type=s["event_type"],
                timestamp=s["timestamp"],
                payload=s["payload"]
            ) for s in steps_raw
        ]
        cols = row.keys()
        return Episode(
            episode_id=row["episode_id"],
            session_id=row["session_id"],
            trace_id=row["trace_id"] if "trace_id" in cols else "unknown",
            start_time=row["start_time"],
            end_time=row["end_time"],
            goal=row["goal"],
            steps=steps,
            outcome=row["outcome"],
            importance=row["importance"],
            consolidated=bool(row["consolidated"])
        )