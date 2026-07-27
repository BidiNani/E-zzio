import sqlite3
import os
import json
import threading
from typing import List, Dict, Any, Optional
from datetime import datetime, timezone
from runtime.recovery.contracts import IncidentBundle

CURRENT_SCHEMA_VERSION = 3

class IncidentStore:
    """Moteur de stockage SQLite avec Migrations pas-à-pas et PRAGMAs d'entreprise."""

    def __init__(self, db_path: str = "data/incidents.db", export_dir: str = "data/incidents/export"):
        os.makedirs(os.path.dirname(db_path), exist_ok=True)
        os.makedirs(export_dir, exist_ok=True)
        self.db_path = db_path
        self.export_dir = export_dir
        self._conn = None
        self._db_lock = threading.RLock()

    def connect(self):
        with self._db_lock:
            if self._conn is None:
                self._conn = sqlite3.connect(self.db_path, timeout=30.0, check_same_thread=False)
                self._conn.execute("PRAGMA journal_mode=WAL;")
                self._conn.execute("PRAGMA synchronous=NORMAL;")
                self._conn.execute("PRAGMA foreign_keys=ON;")
                self._conn.execute("PRAGMA busy_timeout=5000;")
                self._conn.execute("PRAGMA temp_store=MEMORY;")
                self._conn.execute("PRAGMA cache_size=-20000;")
                self._apply_migrations()

    def _apply_migrations(self):
        with self._conn:
            self._conn.execute("CREATE TABLE IF NOT EXISTS incident_schema (version INTEGER PRIMARY KEY)")
            cursor = self._conn.execute("SELECT version FROM incident_schema ORDER BY version DESC LIMIT 1")
            row = cursor.fetchone()
            current_v = row[0] if row else 0

            if current_v < 1:
                self._conn.execute('''
                    CREATE TABLE IF NOT EXISTS incident_bundles (
                        incident_id TEXT PRIMARY KEY,
                        timestamp TEXT NOT NULL,
                        severity TEXT NOT NULL,
                        severity_score INTEGER NOT NULL DEFAULT 10,
                        category TEXT NOT NULL,
                        execution_id TEXT NOT NULL,
                        action_name TEXT NOT NULL,
                        context_valid INTEGER NOT NULL,
                        payload_hash TEXT NOT NULL,
                        bundle_hash TEXT NOT NULL DEFAULT '',
                        state_trace TEXT NOT NULL,
                        telemetry_snapshot TEXT NOT NULL,
                        root_candidates TEXT NOT NULL,
                        metadata TEXT NOT NULL
                    )
                ''')
                current_v = 1

            if current_v < 2:
                try:
                    self._conn.execute("ALTER TABLE incident_bundles ADD COLUMN trace_id TEXT;")
                    self._conn.execute("ALTER TABLE incident_bundles ADD COLUMN span_id TEXT;")
                except sqlite3.OperationalError:
                    pass
                current_v = 2

            if current_v < 3:
                try:
                    self._conn.execute("ALTER TABLE incident_bundles ADD COLUMN findings TEXT DEFAULT '[]';")
                except sqlite3.OperationalError:
                    pass
                current_v = 3

            self._conn.execute("CREATE INDEX IF NOT EXISTS idx_inc_severity ON incident_bundles(severity);")
            self._conn.execute("CREATE INDEX IF NOT EXISTS idx_inc_score ON incident_bundles(severity_score);")
            self._conn.execute("CREATE INDEX IF NOT EXISTS idx_inc_exec ON incident_bundles(execution_id);")
            self._conn.execute("INSERT OR REPLACE INTO incident_schema (version) VALUES (?)", (CURRENT_SCHEMA_VERSION,))

    def save_bundle(self, bundle: IncidentBundle):
        self.connect()
        with self._db_lock:
            with self._conn:
                self._conn.execute('''
                    INSERT OR REPLACE INTO incident_bundles 
                    (incident_id, timestamp, severity, severity_score, category, execution_id, action_name, trace_id, span_id, context_valid, payload_hash, bundle_hash, state_trace, telemetry_snapshot, findings, root_candidates, metadata)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    bundle.incident_id,
                    bundle.timestamp,
                    bundle.severity,
                    bundle.severity_score,
                    bundle.category,
                    bundle.execution_id,
                    bundle.action_name,
                    bundle.trace_id,
                    bundle.span_id,
                    1 if bundle.context_signature_valid else 0,
                    bundle.payload_hash,
                    bundle.bundle_hash,
                    json.dumps(bundle.state_trace, default=str),
                    json.dumps(bundle.telemetry_snapshot, default=str),
                    json.dumps(bundle.findings, default=str),
                    json.dumps(bundle.root_candidates, default=str),
                    json.dumps(bundle.metadata, default=str)
                ))
        self.export_bundle_json(bundle)

    def export_bundle_json(self, bundle: IncidentBundle) -> str:
        filepath = os.path.join(self.export_dir, f"{bundle.incident_id}.json")
        data = {
            "incident_id": bundle.incident_id,
            "timestamp": bundle.timestamp,
            "severity": bundle.severity,
            "severity_score": bundle.severity_score,
            "category": bundle.category,
            "execution_id": bundle.execution_id,
            "action_name": bundle.action_name,
            "trace_id": bundle.trace_id,
            "span_id": bundle.span_id,
            "context_signature_valid": bundle.context_signature_valid,
            "payload_hash": bundle.payload_hash,
            "bundle_hash": bundle.bundle_hash,
            "state_trace": bundle.state_trace,
            "telemetry_snapshot": bundle.telemetry_snapshot,
            "findings": bundle.findings,
            "root_candidates": bundle.root_candidates,
            "metadata": bundle.metadata
        }
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        return filepath

    def get_bundle(self, incident_id: str) -> Optional[Dict[str, Any]]:
        self.connect()
        with self._db_lock:
            cursor = self._conn.execute("SELECT * FROM incident_bundles WHERE incident_id = ?", (incident_id,))
            row = cursor.fetchone()
            if not row: return None
            return {
                "incident_id": row[0],
                "timestamp": row[1],
                "severity": row[2],
                "severity_score": row[3],
                "category": row[4],
                "execution_id": row[5],
                "action_name": row[6],
                "trace_id": row[13] if len(row) > 13 else None,
                "span_id": row[14] if len(row) > 14 else None,
                "context_valid": bool(row[7]),
                "payload_hash": row[8],
                "bundle_hash": row[9],
                "state_trace": json.loads(row[10]),
                "telemetry_snapshot": json.loads(row[11]),
                "root_candidates": json.loads(row[12])
            }

    def close(self):
        with self._db_lock:
            if self._conn:
                self._conn.close()
                self._conn = None
