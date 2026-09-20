import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from core.storage import storage

DB_PATH = Path(r"G:\AI\E-zzio\runtime\state\tasks.db")

TASK_STATES = {
    "DRAFT",
    "SCOPED",
    "PLANNED",
    "POLICY_CHECKED",
    "AWAITING_APPROVAL",
    "RUNNING",
    "VERIFYING",
    "SUCCEEDED",
    "FAILED",
    "CANCELLED",
}

ALLOWED_TRANSITIONS = {
    "DRAFT": {"SCOPED", "CANCELLED"},
    "SCOPED": {"PLANNED", "CANCELLED"},
    "PLANNED": {"POLICY_CHECKED", "CANCELLED"},
    "POLICY_CHECKED": {"AWAITING_APPROVAL", "RUNNING", "CANCELLED"},
    "AWAITING_APPROVAL": {"RUNNING", "CANCELLED"},
    "RUNNING": {"VERIFYING", "FAILED", "CANCELLED"},
    "VERIFYING": {"SUCCEEDED", "FAILED"},
    "SUCCEEDED": set(),
    "FAILED": set(),
    "CANCELLED": set(),
}


def utc_now() -> str:
    return datetime.now(UTC).isoformat()


class TaskManager:
    def __init__(self) -> None:
        self._validate_schema()

    def _validate_schema(self) -> None:
        required = {
            "task_id",
            "title",
            "workspace",
            "state",
            "scope_json",
            "plan_json",
            "approval_id",
            "error_message",
            "created_at",
            "updated_at",
        }

        with storage.get_connection(DB_PATH) as conn:
            conn.execute('''CREATE TABLE IF NOT EXISTS governed_tasks (
                task_id TEXT PRIMARY KEY,
                title TEXT NOT NULL,
                workspace TEXT NOT NULL,
                state TEXT NOT NULL,
                scope_json TEXT NOT NULL,
                plan_json TEXT NOT NULL,
                approval_id TEXT,
                error_message TEXT,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )''')
            conn.commit()
            columns = {row[1] for row in conn.execute('PRAGMA table_info(governed_tasks)')}

        missing = required - columns
        if missing:
            raise RuntimeError(f"tasks.db incompatible ; colonnes absentes : {sorted(missing)}")

    def create_task(
        self,
        task_id: str,
        title: str,
        workspace: str,
        scope: dict[str, Any],
        plan: dict[str, Any] | None = None,
    ) -> str:
        if not task_id.strip():
            raise ValueError("task_id ne peut pas être vide.")
        if not title.strip():
            raise ValueError("title ne peut pas être vide.")
        if not workspace.strip():
            raise ValueError("workspace ne peut pas être vide.")

        now = utc_now()

        with storage.get_connection(DB_PATH) as conn:
            conn.execute(
                """
                INSERT INTO governed_tasks (
                    task_id,
                    title,
                    workspace,
                    state,
                    scope_json,
                    plan_json,
                    approval_id,
                    error_message,
                    created_at,
                    updated_at
                )
                VALUES (?, ?, ?, 'DRAFT', ?, ?, NULL, NULL, ?, ?)
                """,
                (
                    task_id,
                    title,
                    workspace,
                    json.dumps(scope, ensure_ascii=False),
                    json.dumps(plan or {}, ensure_ascii=False),
                    now,
                    now,
                ),
            )

        return task_id

    def get_task(self, task_id: str) -> dict[str, Any] | None:
        with storage.get_connection(DB_PATH) as conn:
            row = conn.execute(
                """
                SELECT
                    task_id,
                    title,
                    workspace,
                    state,
                    scope_json,
                    plan_json,
                    approval_id,
                    error_message,
                    created_at,
                    updated_at
                FROM governed_tasks
                WHERE task_id = ?
                """,
                (task_id,),
            ).fetchone()

        if row is None:
            return None

        return {
            "task_id": row[0],
            "title": row[1],
            "workspace": row[2],
            "state": row[3],
            "scope": json.loads(row[4] or "{}"),
            "plan": json.loads(row[5] or "{}"),
            "approval_id": row[6],
            "error_message": row[7],
            "created_at": row[8],
            "updated_at": row[9],
        }

    def transition_task(
        self,
        task_id: str,
        next_state: str,
        *,
        approval_id: str | None = None,
        error_message: str | None = None,
    ) -> dict[str, Any]:
        if next_state not in TASK_STATES:
            raise ValueError(f"État inconnu : {next_state}")

        task = self.get_task(task_id)
        if task is None:
            raise KeyError(f"Tâche inconnue : {task_id}")

        current_state = task["state"]
        allowed = ALLOWED_TRANSITIONS.get(current_state, set())

        if next_state not in allowed:
            raise ValueError(f"Transition refusée : {current_state} → {next_state}")

        if current_state == "AWAITING_APPROVAL" and next_state == "RUNNING":
            if not approval_id:
                raise PermissionError("approval_id obligatoire pour AWAITING_APPROVAL → RUNNING.")

        with storage.get_connection(DB_PATH) as conn:
            conn.execute(
                """
                UPDATE governed_tasks
                SET
                    state = ?,
                    approval_id = COALESCE(?, approval_id),
                    error_message = COALESCE(?, error_message),
                    updated_at = ?
                WHERE task_id = ?
                """,
                (
                    next_state,
                    approval_id,
                    error_message,
                    utc_now(),
                    task_id,
                ),
            )

        updated = self.get_task(task_id)
        if updated is None:
            raise RuntimeError("Tâche introuvable après mise à jour.")

        return updated


task_manager = TaskManager()
