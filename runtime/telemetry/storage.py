import sqlite3
import os
import json
import hashlib
import threading
from typing import Dict, Any, Optional
from datetime import datetime, timezone, timedelta

CURRENT_SCHEMA_VERSION = 2

class TelemetryStorage:
    """Moteur de stockage persistant durci (v2.6.8) : Thread-safe, Versionné, avec Checksums Forensic."""
    def __init__(self, db_path: str = "data/telemetry.db", retention_days: int = 90):
        os.makedirs(os.path.dirname(db_path), exist_ok=True)
        self.db_path = db_path
        self.retention_days = retention_days
        self._connection_lock = threading.Lock()
        self._init_db()

    def _connect(self) -> sqlite3.Connection:
        """Génère une connexion thread-safe standardisée pour le mode WAL."""
        conn = sqlite3.connect(self.db_path, timeout=30.0, check_same_thread=False)
        conn.execute("PRAGMA journal_mode=WAL;")
        conn.execute("PRAGMA synchronous=NORMAL;")
        return conn

    def _init_db(self):
        with self._connection_lock:
            conn = self._connect()
            try:
                with conn:
                    # 1. Table de schéma
                    conn.execute('''
                        CREATE TABLE IF NOT EXISTS telemetry_schema (
                            version INTEGER PRIMARY KEY,
                            updated_at TEXT NOT NULL
                        )
                    ''')
                    
                    cursor = conn.execute("SELECT version FROM telemetry_schema ORDER BY version DESC LIMIT 1")
                    row = cursor.fetchone()
                    version = row[0] if row else 0
                    
                    # 2. Migrations idempotentes
                    if version < 1:
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
                        now = datetime.now(timezone.utc).isoformat()
                        conn.execute("INSERT INTO telemetry_schema (version, updated_at) VALUES (1, ?)", (now,))
                        version = 1
                        
                    if version < 2:
                        # Migration v2 : Ajout du Checksum Forensic
                        try:
                            conn.execute("ALTER TABLE telemetry_events ADD COLUMN checksum TEXT NOT NULL DEFAULT ''")
                        except sqlite3.OperationalError:
                            pass # La colonne existe déjà
                        
                        now = datetime.now(timezone.utc).isoformat()
                        conn.execute("INSERT INTO telemetry_schema (version, updated_at) VALUES (2, ?)", (now,))
                        version = 2
            finally:
                conn.close()

    def save_metric(self, exec_id: str, action_name: str, status: str, duration_ms: float, cost: float, risk_level: str, category: Optional[str] = None):
        now = datetime.now(timezone.utc).isoformat()
        with self._connection_lock:
            conn = self._connect()
            try:
                with conn:
                    conn.execute('''
                        INSERT INTO telemetry_metrics (exec_id, action_name, status, duration_ms, cost, risk_level, category, timestamp)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    ''', (exec_id, action_name, status, duration_ms, cost, risk_level, category, now))
            finally:
                conn.close()

    def save_event(self, event_id: str, event_type: str, payload: dict, timestamp: float):
        payload_str = json.dumps(payload, sort_keys=True)
        checksum = hashlib.sha256(payload_str.encode('utf-8')).hexdigest()
        
        with self._connection_lock:
            conn = self._connect()
            try:
                with conn:
                    conn.execute('''
                        INSERT INTO telemetry_events (event_id, event_type, payload, checksum, timestamp)
                        VALUES (?, ?, ?, ?, ?)
                    ''', (event_id, event_type, payload_str, checksum, timestamp))
            finally:
                conn.close()

    def enforce_retention(self):
        """Purge automatique des métriques et événements obsolètes."""
        cutoff_date = (datetime.now(timezone.utc) - timedelta(days=self.retention_days)).isoformat()
        cutoff_timestamp = datetime.now(timezone.utc).timestamp() - (self.retention_days * 86400)
        
        with self._connection_lock:
            conn = self._connect()
            try:
                with conn:
                    conn.execute("DELETE FROM telemetry_metrics WHERE timestamp < ?", (cutoff_date,))
                    conn.execute("DELETE FROM telemetry_events WHERE timestamp < ?", (cutoff_timestamp,))
            finally:
                conn.close()

    def get_summary(self) -> Dict[str, Any]:
        with self._connection_lock:
            conn = self._connect()
            try:
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
            finally:
                conn.close()

    def clear(self):
        with self._connection_lock:
            conn = self._connect()
            try:
                with conn:
                    conn.execute("DELETE FROM telemetry_metrics")
                    conn.execute("DELETE FROM telemetry_events")
            finally:
                conn.close()
