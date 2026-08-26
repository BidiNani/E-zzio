import queue
import sqlite3
import threading
import json
import os
from typing import Any, Callable, Optional
from runtime.recovery.contracts import IncidentBundle


class RecoveryEventBus:
    """Bus d'événements asynchrone ultra-résistant avec bascule automatique sur SQLite en cas de congestion."""

    def __init__(self, incident_processor: Optional[Callable[[IncidentBundle], Any]] = None, db_path: str = "data/incidents.db"):
        self.incident_processor = incident_processor
        self.db_path = db_path
        self._queue = queue.Queue(maxsize=100)
        self._worker_thread = None
        self._stop_event = threading.Event()
        self._db_lock = threading.RLock()
        self._init_db()

    def _init_db(self):
        with self._db_lock:
            os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
            conn = sqlite3.connect(self.db_path, timeout=30.0, check_same_thread=False)
            try:
                with conn:
                    conn.execute("PRAGMA journal_mode=WAL;")
                    conn.execute("""
                        CREATE TABLE IF NOT EXISTS overflow_recovery_queue (
                            overflow_id INTEGER PRIMARY KEY AUTOINCREMENT,
                            bundle_json TEXT NOT NULL,
                            timestamp TEXT NOT NULL
                        )
                    """)
            finally:
                conn.close()

    def start(self):
        self._stop_event.clear()
        self._worker_thread = threading.Thread(target=self._worker, daemon=True, name="RecoveryEventWorker")
        self._worker_thread.start()

    def stop(self):
        self._stop_event.set()  # Activation du flag d'arrêt souverain
        if self._worker_thread and self._worker_thread.is_alive():
            self._queue.put(None)
            self._worker_thread.join(timeout=5.0)

    def publish_incident(self, bundle: IncidentBundle):
        try:
            self._queue.put_nowait(bundle)
        except queue.Full:
            self._shelve_overflow(bundle)

    def _shelve_overflow(self, bundle: IncidentBundle):
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
            "state_trace": bundle.state_trace,
            "context_signature_valid": bundle.context_signature_valid,
            "payload_hash": bundle.payload_hash,
            "bundle_hash": bundle.bundle_hash,
            "telemetry_snapshot": bundle.telemetry_snapshot,
            "findings": bundle.findings,
            "root_candidates": bundle.root_candidates,
            "metadata": (bundle.get("metadata") if isinstance(bundle, dict) else getattr(bundle, "metadata", None)),
        }
        with self._db_lock:
            conn = sqlite3.connect(self.db_path, timeout=30.0, check_same_thread=False)
            try:
                with conn:
                    conn.execute(
                        "INSERT INTO overflow_recovery_queue (bundle_json, timestamp) VALUES (?, ?)",
                        (json.dumps(data, default=str), bundle.timestamp),
                    )
            finally:
                conn.close()

    def _process_overflow_backlog(self):
        with self._db_lock:
            conn = sqlite3.connect(self.db_path, timeout=30.0, check_same_thread=False)
            try:
                while True:
                    cursor = conn.execute("SELECT overflow_id, bundle_json FROM overflow_recovery_queue ORDER BY overflow_id ASC LIMIT 50")
                    rows = cursor.fetchall()
                    if not rows:
                        break
                    for overflow_id, bundle_json in rows:
                        raw = json.loads(bundle_json)
                        bundle = IncidentBundle(
                            incident_id=raw["incident_id"],
                            timestamp=raw["timestamp"],
                            severity=raw["severity"],
                            severity_score=raw["severity_score"],
                            category=raw["category"],
                            execution_id=raw["execution_id"],
                            action_name=raw["action_name"],
                            trace_id=raw.get("trace_id"),
                            span_id=raw.get("span_id"),
                            state_trace=raw.get("state_trace", []),
                            context_signature_valid=raw["context_signature_valid"],
                            payload_hash=raw["payload_hash"],
                            bundle_hash=raw["bundle_hash"],
                            telemetry_snapshot=raw.get("telemetry_snapshot", {}),
                            findings=raw.get("findings", []),
                            root_candidates=raw.get("root_candidates", []),
                            metadata=raw.get("metadata", {}),
                        )
                        if self.incident_processor:
                            self.incident_processor(bundle)
                        conn.execute("DELETE FROM overflow_recovery_queue WHERE overflow_id = ?", (overflow_id,))
                    conn.commit()
            finally:
                conn.close()

    def _worker(self):
        while not self._stop_event.is_set():
            try:
                bundle = self._queue.get(timeout=0.1)
                if bundle is None:
                    self._process_overflow_backlog()
                    break
                if self.incident_processor:
                    self.incident_processor(bundle)
            except queue.Empty:
                self._process_overflow_backlog()

        self._process_overflow_backlog()
