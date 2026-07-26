import sqlite3
import os
import json
from typing import List, Dict, Any, Optional
from datetime import datetime, timezone

class ActionStore:
    """Manages persistent storage for action contracts, metadata, and execution history."""
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
                    cost INTEGER DEFAULT 1,
                    timeout REAL DEFAULT 5.0,
                    schema TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                )
            ''')
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
            conn.commit()

    def save_contract(self, action_id: str, version: str, name: str, description: str, permission: str, cost: int, timeout: float, schema: Dict[str, str]):
        now = datetime.now(timezone.utc).isoformat()
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                '''INSERT OR REPLACE INTO action_contracts 
                   (id, version, name, description, permission, cost, timeout, schema, updated_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)''',
                (action_id, version, name, description, permission, cost, timeout, json.dumps(schema, default=str), now)
            )
            conn.commit()

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

    def get_execution_history(self, action_name: Optional[str] = None, limit: int = 50) -> List[Dict[str, Any]]:
        with sqlite3.connect(self.db_path) as conn:
            if action_name:
                cursor = conn.execute(
                    "SELECT exec_id, action_name, status, payload, result, cost, duration_ms, timestamp FROM execution_ledger WHERE action_name = ? ORDER BY timestamp DESC LIMIT ?",
                    (action_name, limit)
                )
            else:
                cursor = conn.execute(
                    "SELECT exec_id, action_name, status, payload, result, cost, duration_ms, timestamp FROM execution_ledger ORDER BY timestamp DESC LIMIT ?",
                    (limit,)
                )
            return [
                {
                    "exec_id": row[0], "action_name": row[1], "status": row[2],
                    "payload": json.loads(row[3]), "result": json.loads(row[4]),
                    "cost": row[5], "duration_ms": row[6], "timestamp": row[7]
                }
                for row in cursor.fetchall()
            ]

    def clear(self):
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("DELETE FROM execution_ledger")
            conn.execute("DELETE FROM action_contracts")
            conn.commit()
