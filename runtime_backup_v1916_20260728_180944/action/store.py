import sqlite3
import os
import json
import hashlib
import uuid
from typing import List, Dict, Tuple, Any, Optional
from datetime import datetime, timezone

class ActionStore:
    """Manages persistent storage with automated schema migrations and cryptographic hash chains."""
    def __init__(self, db_path: str = "data/action_registry.db"):
        os.makedirs(os.path.dirname(db_path), exist_ok=True)
        self.db_path = db_path
        self._init_db()

    def _init_db(self):
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("PRAGMA journal_mode=WAL;")
            conn.execute('''
                CREATE TABLE IF NOT EXISTS action_contracts (
                    id TEXT PRIMARY KEY,
                    version TEXT NOT NULL,
                    name TEXT NOT NULL,
                    description TEXT,
                    permission TEXT NOT NULL,
                    handler_ref TEXT DEFAULT '',
                    cost INTEGER DEFAULT 1,
                    timeout REAL DEFAULT 5.0,
                    risk_level TEXT DEFAULT 'LOW',
                    schema TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                )
            ''')
            try:
                conn.execute("ALTER TABLE action_contracts ADD COLUMN risk_level TEXT DEFAULT 'LOW'")
            except sqlite3.OperationalError:
                pass

            conn.execute('''
                CREATE TABLE IF NOT EXISTS execution_ledger (
                    exec_id TEXT PRIMARY KEY,
                    action_name TEXT NOT NULL,
                    status TEXT NOT NULL,
                    payload TEXT,
                    result TEXT,
                    cost INTEGER,
                    duration_ms REAL,
                    timestamp TEXT NOT NULL
                )
            ''')
            conn.execute('''
                CREATE TABLE IF NOT EXISTS evidence_ledger (
                    evidence_id TEXT PRIMARY KEY,
                    exec_id TEXT NOT NULL,
                    root_trace_id TEXT NOT NULL,
                    action_name TEXT NOT NULL,
                    state TEXT NOT NULL,
                    risk_level TEXT NOT NULL,
                    input_hash TEXT NOT NULL,
                    context_hash TEXT NOT NULL,
                    result_hash TEXT NOT NULL,
                    duration_ms REAL,
                    timestamp TEXT NOT NULL
                )
            ''')
            conn.execute('''
                CREATE TABLE IF NOT EXISTS state_transitions (
                    transition_id TEXT PRIMARY KEY,
                    exec_id TEXT NOT NULL,
                    from_state TEXT NOT NULL,
                    to_state TEXT NOT NULL,
                    transition_hash TEXT DEFAULT '',
                    timestamp TEXT NOT NULL
                )
            ''')
            conn.execute('''
                CREATE TABLE IF NOT EXISTS budget_ledger (
                    event_id TEXT PRIMARY KEY,
                    root_trace_id TEXT NOT NULL,
                    exec_id TEXT NOT NULL,
                    amount INTEGER NOT NULL,
                    remaining INTEGER NOT NULL,
                    timestamp TEXT NOT NULL
                )
            ''')
            conn.commit()

            self._migrate_schema(conn)
            self._repair_transition_hashes(conn)

    def _migrate_schema(self, conn):
        cursor = conn.execute("PRAGMA table_info(state_transitions)")
        columns = {row[1] for row in cursor.fetchall()}

        if "transition_hash" not in columns:
            try:
                conn.execute("ALTER TABLE state_transitions ADD COLUMN transition_hash TEXT DEFAULT ''")
                conn.commit()
            except sqlite3.OperationalError:
                pass

    def _repair_transition_hashes(self, conn):
        rows = conn.execute(
            """
            SELECT transition_id, exec_id, from_state, to_state, timestamp
            FROM state_transitions
            WHERE transition_hash='' OR transition_hash IS NULL
            """
        ).fetchall()

        for row in rows:
            transition_id, exec_id, from_state, to_state, timestamp = row
            raw = f"{exec_id}|{from_state}|{to_state}|{timestamp}"
            digest = hashlib.sha256(raw.encode("utf-8")).hexdigest()

            conn.execute(
                """
                UPDATE state_transitions
                SET transition_hash=?
                WHERE transition_id=?
                """,
                (digest, transition_id)
            )
        conn.commit()

    def save_contract(self, action_id: str, version: str, name: str, description: str, permission: str, handler_ref: str, cost: int, timeout: float, risk_level: str, schema: Dict[str, str]):
        now = datetime.now(timezone.utc).isoformat()
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                '''INSERT OR REPLACE INTO action_contracts 
                   (id, version, name, description, permission, handler_ref, cost, timeout, risk_level, schema, updated_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)''',
                (action_id, version, name, description, permission, handler_ref, cost, timeout, risk_level, json.dumps(schema, default=str), now)
            )
            conn.commit()

    def load_contracts(self) -> List[Dict[str, Any]]:
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("SELECT id, version, name, description, permission, handler_ref, cost, timeout, risk_level, schema FROM action_contracts")
            return [
                {
                    "id": row[0], "version": row[1], "name": row[2],
                    "description": row[3], "permission": row[4], "handler_ref": row[5],
                    "cost": row[6], "timeout": row[7], "risk_level": row[8], "schema": json.loads(row[9])
                }
                for row in cursor.fetchall()
            ]

    def log_execution(self, exec_id: str, action_name: str, status: str, payload: Dict[str, Any], result: Dict[str, Any], cost: int, duration_ms: float):
        now = datetime.now(timezone.utc).isoformat()
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                '''INSERT INTO execution_ledger 
                   (exec_id, action_name, status, payload, result, cost, duration_ms, timestamp)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?)''',
                (exec_id, action_name, status, json.dumps(payload, default=str), json.dumps(result, default=str), cost, duration_ms, now)
            )
            conn.commit()

    def log_transition(self, exec_id: str, from_state: str, to_state: str):
        now = datetime.now(timezone.utc).isoformat()
        transition_id = f"tx_{uuid.uuid4().hex}"
        raw_sig = f"{exec_id}|{from_state}|{to_state}|{now}"
        transition_hash = hashlib.sha256(raw_sig.encode("utf-8")).hexdigest()

        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                '''INSERT INTO state_transitions (transition_id, exec_id, from_state, to_state, transition_hash, timestamp)
                   VALUES (?, ?, ?, ?, ?, ?)''',
                (transition_id, exec_id, from_state, to_state, transition_hash, now)
            )
            conn.commit()

    def get_transition_history(self, exec_id: str) -> List[Tuple[str, str]]:
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute(
                "SELECT from_state, to_state FROM state_transitions WHERE exec_id = ? ORDER BY rowid ASC",
                (exec_id,)
            )
            return [(row[0], row[1]) for row in cursor.fetchall()]

    def get_execution_history(self, action_name: Optional[str] = None, limit: int = 50) -> List[Dict[str, Any]]:
        with sqlite3.connect(self.db_path) as conn:
            if action_name:
                cursor = conn.execute(
                    "SELECT exec_id, action_name, status, payload, result, cost, duration_ms, timestamp FROM execution_ledger WHERE action_name = ? ORDER BY timestamp DESC, rowid DESC LIMIT ?",
                    (action_name, limit)
                )
            else:
                cursor = conn.execute(
                    "SELECT exec_id, action_name, status, payload, result, cost, duration_ms, timestamp FROM execution_ledger ORDER BY rowid DESC LIMIT ?",
                    ( limit,)
                )
            return [
                {
                    "exec_id": row[0], "action_name": row[1], "status": row[2],
                    "payload": json.loads(row[3]), "result": json.loads(row[4]),
                    "cost": row[5], "duration_ms": row[6], "timestamp": row[7]
                }
                for row in cursor.fetchall()
            ]

    def log_evidence(self, exec_id: str, root_trace_id: str, action_name: str, state: str, risk_level: str, payload: dict, context_dict: dict, result: dict, duration_ms: float):
        now = datetime.now(timezone.utc).isoformat()
        in_hash = hashlib.sha256(json.dumps(payload, default=str, sort_keys=True).encode()).hexdigest()
        ctx_hash = hashlib.sha256(json.dumps(context_dict, default=str, sort_keys=True).encode()).hexdigest()
        res_hash = hashlib.sha256(json.dumps(result, default=str, sort_keys=True).encode()).hexdigest()
        evidence_id = f"ev_{exec_id}"

        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                '''INSERT INTO evidence_ledger 
                   (evidence_id, exec_id, root_trace_id, action_name, state, risk_level, input_hash, context_hash, result_hash, duration_ms, timestamp)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)''',
                (evidence_id, exec_id, root_trace_id, action_name, state, risk_level, in_hash, ctx_hash, res_hash, duration_ms, now)
            )
            conn.commit()

    def get_evidence_history(self, limit: int = 50) -> List[Dict[str, Any]]:
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("SELECT evidence_id, exec_id, root_trace_id, action_name, state, risk_level, duration_ms, timestamp FROM evidence_ledger limit ?", ( limit,))
            return [
                {
                    "evidence_id": row[0], "exec_id": row[1], "root_trace_id": row[2],
                    "action_name": row[3], "state": row[4], "risk_level": row[5],
                    "duration_ms": row[6], "timestamp": row[7]
                }
                for row in cursor.fetchall()
            ]

    def clear(self):
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("DELETE FROM execution_ledger")
            conn.execute("DELETE FROM action_contracts")
            conn.execute("DELETE FROM evidence_ledger")
            conn.execute("DELETE FROM state_transitions")
            conn.execute("DELETE FROM budget_ledger")
            conn.commit()








