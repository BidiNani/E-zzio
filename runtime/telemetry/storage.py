import sqlite3
import os
import json
import hashlib
from typing import List, Dict, Any, Optional
from datetime import datetime, timezone, timedelta
from runtime.telemetry.metrics import ExecutionMetric
from runtime.telemetry.events import TelemetryEvent

CURRENT_SCHEMA_VERSION = 3

class TelemetryStorage:
    """Moteur de stockage SQLite Haute Performance (Connexion longue, PRAGMAs durs, Batchs)."""
    def __init__(self, db_path: str = "data/telemetry.db", retention_days: int = 90):
        os.makedirs(os.path.dirname(db_path), exist_ok=True)
        self.db_path = db_path
        self.retention_days = retention_days
        self._conn = None

    def connect(self):
        """Initialise la connexion dédiée au thread d'écriture."""
        if self._conn is None:
            self._conn = sqlite3.connect(self.db_path, timeout=30.0, check_same_thread=False)
            self._conn.execute("PRAGMA journal_mode=WAL;")
            self._conn.execute("PRAGMA synchronous=NORMAL;")
            self._conn.execute("PRAGMA temp_store=MEMORY;")
            self._conn.execute("PRAGMA foreign_keys=ON;")
            self._conn.execute("PRAGMA busy_timeout=5000;")
            self._conn.execute("PRAGMA cache_size=-20000;")
            self._init_schema()

    def _init_schema(self):
        with self._conn:
            self._conn.execute('''CREATE TABLE IF NOT EXISTS telemetry_schema (version INTEGER PRIMARY KEY)''')
            
            cursor = self._conn.execute("SELECT version FROM telemetry_schema ORDER BY version DESC LIMIT 1")
            row = cursor.fetchone()
            version = row[0] if row else 0
            
            if version < 3:
                self._conn.execute('''
                    CREATE TABLE IF NOT EXISTS telemetry_metrics (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        exec_id TEXT NOT NULL,
                        action_name TEXT NOT NULL,
                        status TEXT NOT NULL,
                        duration_ms REAL NOT NULL,
                        cost REAL NOT NULL,
                        risk_level TEXT NOT NULL,
                        category TEXT,
                        trace_id TEXT,
                        span_id TEXT,
                        session_id TEXT,
                        error_stack_hash TEXT,
                        thread_id INTEGER,
                        hostname TEXT,
                        timestamp TEXT NOT NULL
                    )
                ''')
                self._conn.execute('''
                    CREATE TABLE IF NOT EXISTS telemetry_events (
                        event_id TEXT PRIMARY KEY,
                        event_type TEXT NOT NULL,
                        payload TEXT NOT NULL,
                        checksum TEXT NOT NULL,
                        timestamp REAL NOT NULL
                    )
                ''')
                
                # INDEXES STRATÉGIQUES POUR DASHBOARDS TEMPS RÉEL
                self._conn.execute("CREATE INDEX IF NOT EXISTS idx_status ON telemetry_metrics(status);")
                self._conn.execute("CREATE INDEX IF NOT EXISTS idx_category ON telemetry_metrics(category);")
                self._conn.execute("CREATE INDEX IF NOT EXISTS idx_timestamp ON telemetry_metrics(timestamp);")
                self._conn.execute("CREATE INDEX IF NOT EXISTS idx_action ON telemetry_metrics(action_name);")
                
                self._conn.execute("INSERT OR REPLACE INTO telemetry_schema (version) VALUES (3)")

    def save_metrics_batch(self, metrics: List[ExecutionMetric]):
        if not self._conn: return
        query = '''
            INSERT INTO telemetry_metrics 
            (exec_id, action_name, status, duration_ms, cost, risk_level, category, trace_id, span_id, session_id, error_stack_hash, thread_id, hostname, timestamp)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        '''
        now = datetime.now(timezone.utc).isoformat()
        data = [
            (m.exec_id, m.action_name, m.status, m.duration_ms, m.cost, m.risk_level, m.category, 
             m.trace_id, m.span_id, m.session_id, m.error_stack_hash, m.thread_id, m.hostname, now)
            for m in metrics
        ]
        with self._conn:
            self._conn.executemany(query, data)

    def save_events_batch(self, events: List[TelemetryEvent]):
        if not self._conn: return
        query = "INSERT INTO telemetry_events (event_id, event_type, payload, checksum, timestamp) VALUES (?, ?, ?, ?, ?)"
        data = []
        for e in events:
            payload_str = json.dumps(e.payload, sort_keys=True)
            chk = hashlib.sha256(payload_str.encode('utf-8')).hexdigest()
            data.append((e.event_id, e.event_type.value if hasattr(e.event_type, 'value') else str(e.event_type), payload_str, chk, e.timestamp))
        with self._conn:
            self._conn.executemany(query, data)

    def enforce_retention(self):
        if not self._conn: return
        cutoff_date = (datetime.now(timezone.utc) - timedelta(days=self.retention_days)).isoformat()
        cutoff_timestamp = datetime.now(timezone.utc).timestamp() - (self.retention_days * 86400)
        with self._conn:
            self._conn.execute("DELETE FROM telemetry_metrics WHERE timestamp < ?", (cutoff_date,))
            self._conn.execute("DELETE FROM telemetry_events WHERE timestamp < ?", (cutoff_timestamp,))
            
    def get_summary(self) -> Dict[str, Any]:
        """Agrégation avancée : Taux d'erreur, budget, latence, percentiles."""
        if not self._conn: return {}
        cursor = self._conn.execute('''
            SELECT 
                COUNT(*), 
                SUM(CASE WHEN status='SUCCESS' THEN 1 ELSE 0 END), 
                SUM(cost),
                MIN(timestamp),
                MAX(timestamp)
            FROM telemetry_metrics
        ''')
        row = cursor.fetchone()
        total, successes, total_cost, t_min, t_max = row[0] or 0, row[1] or 0, row[2] or 0.0, row[3], row[4]
        
        # Approximation P50, P90, P99 en Python sur un échantillon récent
        cursor = self._conn.execute("SELECT duration_ms FROM telemetry_metrics ORDER BY timestamp DESC LIMIT 1000")
        durations = sorted([r[0] for r in cursor.fetchall()])
        
        p50 = durations[int(len(durations)*0.5)] if durations else 0
        p90 = durations[int(len(durations)*0.9)] if durations else 0
        p99 = durations[int(len(durations)*0.99)] if durations else 0
        mean_lat = sum(durations)/len(durations) if durations else 0
        
        # Calcul du débit (Events/sec)
        throughput = 0.0
        if t_min and t_max:
            t1 = datetime.fromisoformat(t_min)
            t2 = datetime.fromisoformat(t_max)
            delta_sec = (t2 - t1).total_seconds()
            if delta_sec > 0: throughput = total / delta_sec
            
        cursor_err = self._conn.execute("SELECT category, COUNT(*) FROM telemetry_metrics WHERE category IS NOT NULL GROUP BY category")
        error_breakdown = {r[0]: r[1] for r in cursor_err.fetchall()}

        return {
            "total_executions": total,
            "success_rate": round(successes / total, 4) if total > 0 else 1.0,
            "latency": {"mean": round(mean_lat,2), "p50": p50, "p90": p90, "p99": p99},
            "throughput_eps": round(throughput, 2),
            "total_budget_consumed": round(total_cost, 2),
            "error_breakdown": error_breakdown
        }

    def close(self):
        if self._conn:
            self._conn.close()
            self._conn = None
