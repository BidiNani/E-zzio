import json
import sqlite3
from pathlib import Path
from typing import Protocol

from core.tasks.models import Task, TaskState


class ITaskStore(Protocol):  # pragma: no cover (Protocol stub : pas de logique metier)
    def save(self, task: Task) -> None: ...
    def get_by_id(self, task_id: str) -> Task | None: ...
    def list_by_state(self, state: TaskState) -> list[Task]: ...


class SqliteTaskStore:
    def __init__(self, db_path: Path):
        self.db_path = db_path
        self._init_db()

    def _get_connection(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self) -> None:
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        with self._get_connection() as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS governed_tasks (
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
                );
            """)
            conn.execute("CREATE INDEX IF NOT EXISTS idx_tasks_state ON governed_tasks(state);")
            conn.commit()

    def save(self, task: Task) -> None:
        with self._get_connection() as conn:
            conn.execute(
                """
                INSERT INTO governed_tasks (
                    task_id, title, workspace, state, scope_json,
                    plan_json, approval_id, error_message, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(task_id) DO UPDATE SET
                    state = excluded.state,
                    scope_json = excluded.scope_json,
                    plan_json = excluded.plan_json,
                    approval_id = excluded.approval_id,
                    error_message = excluded.error_message,
                    updated_at = excluded.updated_at;
            """,
                (
                    task.task_id,
                    task.title,
                    task.workspace,
                    task.state.value,
                    json.dumps(task.scope),
                    json.dumps(task.plan),
                    task.approval_id,
                    task.error_message,
                    task.created_at,
                    task.updated_at,
                ),
            )
            conn.commit()

    def get_by_id(self, task_id: str) -> Task | None:
        with self._get_connection() as conn:
            row = conn.execute("SELECT * FROM governed_tasks WHERE task_id = ?", (task_id,)).fetchone()
            if not row:
                return None
            return self._row_to_task(row)

    def list_by_state(self, state: TaskState) -> list[Task]:
        with self._get_connection() as conn:
            rows = conn.execute("SELECT * FROM governed_tasks WHERE state = ?", (state.value,)).fetchall()
            return [self._row_to_task(row) for row in rows]

    def _row_to_task(self, row: sqlite3.Row) -> Task:
        return Task(
            task_id=row["task_id"],
            title=row["title"],
            workspace=row["workspace"],
            state=TaskState(row["state"]),
            scope=json.loads(row["scope_json"]),
            plan=json.loads(row["plan_json"]),
            approval_id=row["approval_id"],
            error_message=row["error_message"],
            created_at=row["created_at"],
            updated_at=row["updated_at"],
        )
