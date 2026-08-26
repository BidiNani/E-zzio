import os
import sys
import sqlite3
import json
from pathlib import Path
from datetime import datetime, timezone

ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

DB_PATH = ROOT_DIR / "runtime" / "telemetry" / "provider_events.db"
PERFORMANCE_CACHE_PATH = ROOT_DIR / "runtime" / "metrics" / "provider_performance.json"


class DurableTelemetry:
    def __init__(self):
        DB_PATH.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def _get_connection(self):
        conn = sqlite3.connect(str(DB_PATH), timeout=15.0)
        conn.row_factory = sqlite3.Row
        # Activation stricte des pragmas de résilience
        conn.execute("PRAGMA journal_mode=WAL;")
        conn.execute("PRAGMA synchronous=NORMAL;")
        conn.execute("PRAGMA busy_timeout=5000;")
        conn.execute("PRAGMA foreign_keys=ON;")
        return conn

    def _init_db(self):
        with self._get_connection() as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS provider_events (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TEXT NOT NULL,
                    provider TEXT NOT NULL,
                    model TEXT,
                    capability TEXT,
                    success INTEGER NOT NULL,
                    latency_ms REAL,
                    error_type TEXT,
                    quota_state TEXT,
                    key_index INTEGER,
                    request_id TEXT
                )
            """)
            conn.commit()

    def record_event(
        self,
        provider: str,
        model: str,
        capability: str,
        success: bool,
        latency_ms: float,
        error_type: str = None,
        quota_state: str = "available",
        key_index: int = 0,
        request_id: str = "none",
    ):
        timestamp = datetime.now(timezone.utc).isoformat()
        with self._get_connection() as conn:
            conn.execute(
                """
                INSERT INTO provider_events
                (timestamp, provider, model, capability, success, latency_ms, error_type, quota_state, key_index, request_id)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
                (timestamp, provider, model, capability, 1 if success else 0, latency_ms, error_type, quota_state, key_index, request_id),
            )
            conn.commit()

        self._rebuild_performance_cache_atomic()

    def _rebuild_performance_cache_atomic(self):
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT DISTINCT provider FROM provider_events")
            providers = [row["provider"] for row in cursor.fetchall()]

            cache_data = {
                "schema_version": "V1.2-HARDENED-TELEMETRY",
                "updated_at": datetime.now(timezone.utc).isoformat(),
                "providers": {},
            }

            for p in providers:
                cursor.execute(
                    """
                    SELECT COUNT(*) as calls, SUM(success) as success_count, AVG(latency_ms) as avg_latency
                    FROM provider_events WHERE provider = ?
                """,
                    (p,),
                )
                row = cursor.fetchone()
                calls = row["calls"] or 0
                success = row["success_count"] or 0
                errors = calls - success

                raw_success_rate = (success / calls) if calls > 0 else 0.5
                confidence = round(min(1.0, calls / 100.0), 2)

                # Formule de Cold Start (Pondération de fiabilité)
                effective_reliability = (raw_success_rate * confidence) + (0.5 * (1.0 - confidence))

                cache_data["providers"][p] = {
                    "calls": calls,
                    "success": success,
                    "errors": errors,
                    "raw_success_rate": round(raw_success_rate, 3),
                    "confidence": confidence,
                    "effective_reliability": round(effective_reliability, 3),
                    "avg_latency_ms": round(row["avg_latency"] or 0.0, 2),
                }

            PERFORMANCE_CACHE_PATH.parent.mkdir(parents=True, exist_ok=True)
            tmp_path = PERFORMANCE_CACHE_PATH.with_suffix(".tmp")
            tmp_path.write_text(json.dumps(cache_data, indent=2, ensure_ascii=False), encoding="utf-8")
            os.replace(tmp_path, PERFORMANCE_CACHE_PATH)  # Atomic sur Windows


provider_telemetry = DurableTelemetry()
