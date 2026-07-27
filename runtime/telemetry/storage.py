import sqlite3
import os
import json
from typing import Dict, Any, Optional
from datetime import datetime, timezone

class TelemetryStorage:
    """Moteur de stockage persistant dédié à l'observabilité (data/telemetry.db)."""
    def __init__(self, db_path: str = "data/telemetry.db"):
        os.makedirs(os.path.dirname(db_path), exist_ok=True)
        self.db_path = db_path
        self._init_db()

    def _init_db(self):
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("PRAGMA journal_mode=WAL;")
            conn.execute('''
                CREATE TABLE IF NOT EXISTS telemetry_metrics (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    exec_id TEXT NOT NULL,
                    action_name TEXT NOT NULL,
                    status TEXT NOT NULL,
                    duration_ms REAL NOT NULL,
                    cost REAL NOT NULL,
                    risk_level TEXT NOT NULL,
                    category TEXT,
                    timestamp TEXT NOT NULL
                )
            ''')
            conn.execute('''
                CREATE TABLE IF NOT EXISTS telemetry_events (
                    event_id TEXT PRIMARY KEY,
                    event_type TEXT NOT NULL,
                    payload TEXT NOT NULL,
                    timestamp REAL NOT NULL
                )
            ''')
            conn.commit()

    def save_metric(self, exec_id: str, action_name: str, status: str, duration_ms: float, cost: float, risk_level: str, category: Optional[str] = None):
        now = datetime.now(timezone.utc).isoformat()
        with sqlite3.connect(self.db_path) as conn:
            conn.execute('''
                INSERT INTO telemetry_metrics (exec_id, action_name, status, duration_ms, cost, risk_level, category, timestamp)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ''', (exec_id, action_name, status, duration_ms, cost, risk_level, category, now))
            conn.commit()

    def save_event(self, event_id: str, event_type: str, payload: dict, timestamp: float):
        with sqlite3.connect(self.db_path) as conn:
            conn.execute('''
                INSERT INTO telemetry_events (event_id, event_type, payload, timestamp)
                VALUES (?, ?, ?, ?)
            ''', (event_id, event_type, json.dumps(payload, default=str), timestamp))
            conn.commit()

    def get_summary(self) -> Dict[str, Any]:
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("SELECT COUNT(*), SUM(CASE WHEN status='SUCCESS' THEN 1 ELSE 0 END), AVG(duration_ms) FROM telemetry_metrics")
            row = cursor.fetchone()
            total = row[0] or 0
            successes = row[1] or 0
            avg_duration = row[2] or 0.0

            cursor_err = conn.execute("SELECT category, COUNT(*) FROM telemetry_metrics WHERE category IS NOT NULL GROUP BY category")
            error_breakdown = {r[0]: r[1] for r in cursor_err.fetchall()}

            return {
                "total_executions": total,
                "success_rate": round(successes / total, 4) if total > 0 else 1.0,
                "mean_latency_ms": round(avg_duration, 2),
                "error_breakdown": error_breakdown
            }

    def clear(self):
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("DELETE FROM telemetry_metrics")
            conn.execute("DELETE FROM telemetry_events")
            conn.commit()
