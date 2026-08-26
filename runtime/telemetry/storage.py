import sqlite3
import os
import json
import hashlib
import threading
import statistics
from typing import List, Dict, Any
from datetime import datetime, timezone, timedelta
from runtime.telemetry.metrics import ExecutionMetric
from runtime.telemetry.events import TelemetryEvent

CURRENT_SCHEMA_VERSION = 4


class TelemetryStorage:
    """Stockage SQLite v2.6.9 : Exports OTLP / Prometheus & Requêtes analytiques."""

    def __init__(self, db_path: str = "data/telemetry.db", retention_days: int = 90):
        os.makedirs(os.path.dirname(db_path), exist_ok=True)
        self.db_path = db_path
        self.retention_days = retention_days
        self._conn = None
        self._db_lock = threading.RLock()

    def connect(self):
        with self._db_lock:
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
            self._conn.execute("CREATE TABLE IF NOT EXISTS telemetry_schema (version INTEGER PRIMARY KEY)")
            cursor = self._conn.execute("SELECT version FROM telemetry_schema ORDER BY version DESC LIMIT 1")
            row = cursor.fetchone()
            version = row[0] if row else 0

            if version < 4:
                self._conn.execute("""
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
                        payload_size_bytes INTEGER DEFAULT 0,
                        thread_id INTEGER,
                        hostname TEXT,
                        timestamp TEXT NOT NULL
                    )
                """)
                self._conn.execute("""
                    CREATE TABLE IF NOT EXISTS telemetry_events (
                        event_id TEXT PRIMARY KEY,
                        event_type TEXT NOT NULL,
                        payload TEXT NOT NULL,
                        checksum TEXT NOT NULL,
                        timestamp REAL NOT NULL
                    )
                """)

                self._conn.execute("CREATE INDEX IF NOT EXISTS idx_status ON telemetry_metrics(status);")
                self._conn.execute("CREATE INDEX IF NOT EXISTS idx_category ON telemetry_metrics(category);")
                self._conn.execute("CREATE INDEX IF NOT EXISTS idx_timestamp ON telemetry_metrics(timestamp);")
                self._conn.execute("CREATE INDEX IF NOT EXISTS idx_action ON telemetry_metrics(action_name);")
                self._conn.execute("INSERT OR REPLACE INTO telemetry_schema (version) VALUES (4)")

    def save_metrics_batch(self, metrics: List[ExecutionMetric]):
        if not metrics:
            return
        query = """
            INSERT INTO telemetry_metrics
            (exec_id, action_name, status, duration_ms, cost, risk_level, category, trace_id, span_id, session_id, error_stack_hash, payload_size_bytes, thread_id, hostname, timestamp)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """
        now = datetime.now(timezone.utc).isoformat()
        data = [
            (
                m.exec_id,
                m.action_name,
                m.status,
                m.duration_ms,
                m.cost,
                m.risk_level,
                m.category,
                m.trace_id,
                m.span_id,
                m.session_id,
                m.error_stack_hash,
                m.payload_size_bytes,
                m.thread_id,
                m.hostname,
                now,
            )
            for m in metrics
        ]
        with self._db_lock:
            if self._conn:
                with self._conn:
                    self._conn.executemany(query, data)

    def save_events_batch(self, events: List[TelemetryEvent]):
        if not events:
            return
        query = "INSERT INTO telemetry_events (event_id, event_type, payload, checksum, timestamp) VALUES (?, ?, ?, ?, ?)"
        data = []
        for e in events:
            payload_str = json.dumps(e.payload, sort_keys=True)
            chk = hashlib.sha256(payload_str.encode("utf-8")).hexdigest()
            data.append(
                (e.event_id, e.event_type.value if hasattr(e.event_type, "value") else str(e.event_type), payload_str, chk, e.timestamp)
            )
        with self._db_lock:
            if self._conn:
                with self._conn:
                    self._conn.executemany(query, data)

    def export_prometheus(self) -> str:
        """Exporte les métriques système au format standard Prometheus TSDB."""
        summary = self.get_summary()
        lines = [
            "# HELP ezzio_executions_total Total actions executed",
            "# TYPE ezzio_executions_total counter",
            f"ezzio_executions_total {summary.get('total_executions', 0)}",
            "# HELP ezzio_success_rate Taux de succes des actions",
            "# TYPE ezzio_success_rate gauge",
            f"ezzio_success_rate {summary.get('success_rate', 1.0)}",
            "# HELP ezzio_latency_p90_ms Latence P90 en millisecondes",
            "# TYPE ezzio_latency_p90_ms gauge",
            f"ezzio_latency_p90_ms {summary.get('latency', {}).get('p90', 0.0)}",
            "# HELP ezzio_budget_consumed_total Budget total consomme",
            "# TYPE ezzio_budget_consumed_total counter",
            f"ezzio_budget_consumed_total {summary.get('total_budget_consumed', 0.0)}",
        ]
        return "\n".join(lines)

    def export_otlp_spans(self, limit: int = 100) -> List[Dict[str, Any]]:
        """Génère un tableau de Spans OTLP (OpenTelemetry) pour export externe."""
        with self._db_lock:
            if not self._conn:
                return []
            cursor = self._conn.execute(
                "SELECT exec_id, action_name, status, duration_ms, trace_id, span_id, timestamp FROM telemetry_metrics ORDER BY timestamp DESC LIMIT ?",
                (limit,),
            )
            spans = []
            for row in cursor.fetchall():
                spans.append(
                    {
                        "traceId": row[4] or f"trace_{row[0]}",
                        "spanId": row[5] or f"span_{row[0]}",
                        "name": row[1],
                        "kind": "SPAN_KIND_INTERNAL",
                        "attributes": {"status": row[2], "duration_ms": row[3]},
                        "timestamp": row[6],
                    }
                )
            return spans

    def run_maintenance(self):
        with self._db_lock:
            if self._conn:
                self._conn.execute("PRAGMA optimize;")
                self._conn.execute("VACUUM;")

    def enforce_retention(self):
        cutoff_date = (datetime.now(timezone.utc) - timedelta(days=self.retention_days)).isoformat()
        cutoff_timestamp = datetime.now(timezone.utc).timestamp() - (self.retention_days * 86400)
        with self._db_lock:
            if self._conn:
                with self._conn:
                    self._conn.execute("DELETE FROM telemetry_metrics WHERE timestamp < ?", (cutoff_date,))
                    self._conn.execute("DELETE FROM telemetry_events WHERE timestamp < ?", (cutoff_timestamp,))

    def get_summary(s) -> Dict[str, Any]:
        with s._db_lock:
            if not s._conn:
                return {}
            cursor = s._conn.execute("""
                SELECT COUNT(*), SUM(CASE WHEN status='SUCCESS' THEN 1 ELSE 0 END), SUM(cost), MIN(timestamp), MAX(timestamp)
                FROM telemetry_metrics
            """)
            row = cursor.fetchone()
            total, successes, total_cost, t_min, t_max = row[0] or 0, row[1] or 0, row[2] or 0.0, row[3], row[4]

            cursor = s._conn.execute("SELECT duration_ms FROM telemetry_metrics ORDER BY timestamp DESC LIMIT 1000")
            durations = [r[0] for r in cursor.fetchall()]

            mean_lat = statistics.mean(durations) if durations else 0.0
            if len(durations) >= 2:
                quantiles = statistics.quantiles(durations, n=100)
                p50, p90, p99 = quantiles[49], quantiles[89], quantiles[98]
            elif durations:
                p50 = p90 = p99 = durations[0]
            else:
                p50 = p90 = p99 = 0.0

            throughput = 0.0
            if t_min and t_max:
                try:
                    delta_sec = (datetime.fromisoformat(t_max) - datetime.fromisoformat(t_min)).total_seconds()
                    if delta_sec > 0:
                        throughput = total / delta_sec
                except Exception:
                    pass

            cursor_err = s._conn.execute("SELECT category, COUNT(*) FROM telemetry_metrics WHERE category IS NOT NULL GROUP BY category")
            error_breakdown = {r[0]: r[1] for r in cursor_err.fetchall()}

            return {
                "total_executions": total,
                "success_rate": round(successes / total, 4) if total > 0 else 1.0,
                "latency": {"mean": round(mean_lat, 2), "p50": round(p50, 2), "p90": round(p90, 2), "p99": round(p99, 2)},
                "throughput_eps": round(throughput, 2),
                "total_budget_consumed": round(total_cost, 2),
                "error_breakdown": error_breakdown,
            }

    def close(self):
        with self._db_lock:
            if self._conn:
                self._conn.close()
                self._conn = None
