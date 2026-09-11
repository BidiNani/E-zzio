"""
E-ZZIO Sovereign Governance — SQLite Store for Approval Requests.
Gère la persistance atomique, les transactions WAL et l'intégrité de la table `approval_requests`.
"""
from __future__ import annotations

import json
import sqlite3
import threading
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Optional, Tuple

from core.governance.approval.models import (
    ApprovalRequest,
    ApprovalStatus,
    ExecutionState,
)
from core.storage import storage

DEFAULT_DB_PATH = Path(r"G:\AI\E-zzio\runtime\state\tasks.db")


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


class SqliteApprovalStore:
    def __init__(self, db_path: Path | str = DEFAULT_DB_PATH):
        self.db_path = Path(db_path)
        self._lock = threading.Lock()
        self._init_db()

    def _get_raw_connection(self) -> sqlite3.Connection:
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        conn = sqlite3.connect(self.db_path, timeout=10.0, check_same_thread=False)
        conn.execute("PRAGMA journal_mode=WAL;")
        conn.execute("PRAGMA busy_timeout=5000;")
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self) -> None:
        with self._lock:
            with self._get_raw_connection() as conn:
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS approval_requests (
                        approval_id TEXT PRIMARY KEY,
                        task_id TEXT NOT NULL,
                        session_id TEXT NOT NULL,
                        agent_id TEXT NOT NULL,
                        capability_name TEXT NOT NULL,
                        scope TEXT NOT NULL,
                        safe_summary TEXT NOT NULL,
                        payload_hash TEXT NOT NULL,
                        params_payload TEXT NOT NULL,
                        status TEXT NOT NULL DEFAULT 'PENDING',
                        requested_by TEXT NOT NULL,
                        requested_at TEXT NOT NULL,
                        expires_at TEXT NOT NULL,
                        decided_by TEXT,
                        decided_at TEXT,
                        decision_reason TEXT,
                        execution_state TEXT NOT NULL DEFAULT 'NOT_STARTED',
                        consumed_at TEXT,
                        result_cache TEXT
                    );
                """)
                conn.execute("CREATE INDEX IF NOT EXISTS idx_approvals_status_expires ON approval_requests(status, expires_at);")
                conn.execute("CREATE INDEX IF NOT EXISTS idx_approvals_task_id ON approval_requests(task_id);")
                conn.commit()

    def save_request(self, req: ApprovalRequest) -> None:
        with self._lock:
            with self._get_raw_connection() as conn:
                conn.execute("""
                    INSERT INTO approval_requests (
                        approval_id, task_id, session_id, agent_id, capability_name, scope,
                        safe_summary, payload_hash, params_payload, status, requested_by,
                        requested_at, expires_at, decided_by, decided_at, decision_reason,
                        execution_state, consumed_at, result_cache
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ON CONFLICT(approval_id) DO UPDATE SET
                        status = excluded.status,
                        decided_by = excluded.decided_by,
                        decided_at = excluded.decided_at,
                        decision_reason = excluded.decision_reason,
                        execution_state = excluded.execution_state,
                        consumed_at = excluded.consumed_at,
                        result_cache = excluded.result_cache;
                """, (
                    req.approval_id, req.task_id, req.session_id, req.agent_id,
                    req.capability_name, req.scope, req.safe_summary, req.payload_hash,
                    req.params_payload, req.status.value, req.requested_by,
                    req.requested_at, req.expires_at, req.decided_by,
                    req.decided_at, req.decision_reason, req.execution_state.value,
                    req.consumed_at, req.result_cache
                ))
                conn.commit()

    def get_by_id(self, approval_id: str) -> Optional[ApprovalRequest]:
        with self._lock:
            with self._get_raw_connection() as conn:
                row = conn.execute(
                    "SELECT * FROM approval_requests WHERE approval_id = ?",
                    (approval_id,)
                ).fetchone()
                if not row:
                    return None
                return self._row_to_request(row)

    def list_pending(self) -> List[ApprovalRequest]:
        with self._lock:
            with self._get_raw_connection() as conn:
                rows = conn.execute(
                    "SELECT * FROM approval_requests WHERE status = 'PENDING' ORDER BY requested_at ASC"
                ).fetchall()
                return [self._row_to_request(r) for r in rows]

    def update_decision_atomic(
        self,
        approval_id: str,
        new_status: ApprovalStatus,
        decided_by: str,
        decided_at: str,
        reason: Optional[str] = None,
    ) -> Tuple[bool, Optional[ApprovalRequest], str]:
        """Met à jour la décision sous transaction immédiate pour éviter tout TOCTOU."""
        with self._lock:
            conn = self._get_raw_connection()
            try:
                conn.execute("BEGIN IMMEDIATE;")
                row = conn.execute(
                    "SELECT * FROM approval_requests WHERE approval_id = ?",
                    (approval_id,)
                ).fetchone()
                if not row:
                    conn.rollback()
                    return False, None, "APPROVAL_NOT_FOUND"

                current_status = row["status"]
                expires_at = row["expires_at"]
                now_str = utc_now()

                # Vérification TTL
                if current_status == ApprovalStatus.PENDING.value and now_str >= expires_at:
                    conn.execute(
                        "UPDATE approval_requests SET status = 'EXPIRED' WHERE approval_id = ?",
                        (approval_id,)
                    )
                    conn.commit()
                    updated_row = conn.execute("SELECT * FROM approval_requests WHERE approval_id = ?", (approval_id,)).fetchone()
                    return False, self._row_to_request(updated_row), "APPROVAL_EXPIRED"

                if current_status != ApprovalStatus.PENDING.value:
                    conn.rollback()
                    return False, self._row_to_request(row), f"INVALID_STATUS_TRANSITION_FROM_{current_status}"

                conn.execute("""
                    UPDATE approval_requests
                    SET status = ?, decided_by = ?, decided_at = ?, decision_reason = ?
                    WHERE approval_id = ?
                """, (new_status.value, decided_by, decided_at, reason, approval_id))
                conn.commit()

                updated_row = conn.execute("SELECT * FROM approval_requests WHERE approval_id = ?", (approval_id,)).fetchone()
                return True, self._row_to_request(updated_row), "OK"
            except Exception as e:
                conn.rollback()
                raise e
            finally:
                conn.close()

    def claim_execution_atomic(
        self,
        approval_id: str,
    ) -> Tuple[bool, Optional[ApprovalRequest], str]:
        """
        Revendique le droit exclusif d'exécuter la requête approuvée.
        Passe atomiquement l'état d'exécution à RUNNING.
        Garantit 1 seul gagnant sous concurrence (Double execution barrier).
        """
        with self._lock:
            conn = self._get_raw_connection()
            try:
                conn.execute("BEGIN IMMEDIATE;")
                row = conn.execute(
                    "SELECT * FROM approval_requests WHERE approval_id = ?",
                    (approval_id,)
                ).fetchone()
                if not row:
                    conn.rollback()
                    return False, None, "APPROVAL_NOT_FOUND"

                req = self._row_to_request(row)
                now_str = utc_now()

                # Vérifications strictes
                if req.status != ApprovalStatus.APPROVED:
                    conn.rollback()
                    return False, req, f"NOT_APPROVED_STATUS_{req.status.value}"

                if now_str >= req.expires_at:
                    conn.execute("UPDATE approval_requests SET status = 'EXPIRED' WHERE approval_id = ?", (approval_id,))
                    conn.commit()
                    return False, self._row_to_request(conn.execute("SELECT * FROM approval_requests WHERE approval_id = ?", (approval_id,)).fetchone()), "APPROVAL_EXPIRED"

                if req.execution_state == ExecutionState.CONSUMED:
                    conn.rollback()
                    return False, req, "ALREADY_CONSUMED"

                if req.execution_state == ExecutionState.RUNNING:
                    conn.rollback()
                    return False, req, "ALREADY_RUNNING"

                # Verrouille l'exécution
                conn.execute("""
                    UPDATE approval_requests
                    SET execution_state = 'RUNNING'
                    WHERE approval_id = ?
                """, (approval_id,))
                conn.commit()

                updated_row = conn.execute("SELECT * FROM approval_requests WHERE approval_id = ?", (approval_id,)).fetchone()
                return True, self._row_to_request(updated_row), "OK"
            except Exception as e:
                conn.rollback()
                raise e
            finally:
                conn.close()

    def finalize_execution_atomic(
        self,
        approval_id: str,
        success: bool,
        result_cache: Optional[str] = None,
    ) -> None:
        """Finalise l'exécution en CONSUMED (si succès) ou FAILED_DURING_EXECUTION."""
        with self._lock:
            conn = self._get_raw_connection()
            try:
                conn.execute("BEGIN IMMEDIATE;")
                now_str = utc_now()
                final_exec_state = ExecutionState.CONSUMED.value if success else ExecutionState.FAILED_DURING_EXECUTION.value
                conn.execute("""
                    UPDATE approval_requests
                    SET execution_state = ?, consumed_at = ?, result_cache = ?
                    WHERE approval_id = ?
                """, (final_exec_state, now_str, result_cache, approval_id))
                conn.commit()
            except Exception as e:
                conn.rollback()
                raise e
            finally:
                conn.close()

    def _row_to_request(self, row: sqlite3.Row) -> ApprovalRequest:
        return ApprovalRequest(
            approval_id=row["approval_id"],
            task_id=row["task_id"],
            session_id=row["session_id"],
            agent_id=row["agent_id"],
            capability_name=row["capability_name"],
            scope=row["scope"],
            safe_summary=row["safe_summary"],
            payload_hash=row["payload_hash"],
            params_payload=row["params_payload"],
            status=ApprovalStatus(row["status"]),
            requested_by=row["requested_by"],
            requested_at=row["requested_at"],
            expires_at=row["expires_at"],
            decided_by=row["decided_by"],
            decided_at=row["decided_at"],
            decision_reason=row["decision_reason"],
            execution_state=ExecutionState(row["execution_state"]),
            consumed_at=row["consumed_at"],
            result_cache=row["result_cache"],
        )
