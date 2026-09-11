import sqlite3
from pathlib import Path

import pytest

from core.tasks import manager


def create_task_schema(db_path: Path) -> None:
    with sqlite3.connect(db_path) as conn:
        conn.execute("""
            CREATE TABLE governed_tasks (
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
            )
        """)


def make_manager(monkeypatch, tmp_path: Path, filename: str):
    db_path = tmp_path / filename
    create_task_schema(db_path)
    monkeypatch.setattr(manager, "DB_PATH", db_path)
    return manager.TaskManager()


def create_draft(local_manager, task_id: str):
    return local_manager.create_task(
        task_id=task_id,
        title="Analyser E-ZZIO",
        workspace=r"G:\AI\E-zzio",
        scope={"mode": "read_only"},
        plan={"steps": ["inventory", "report"]},
    )


def test_create_and_read_governed_task(monkeypatch, tmp_path: Path):
    local_manager = make_manager(monkeypatch, tmp_path, "tasks_create.db")
    task_id = create_draft(local_manager, "task_test_001")

    task = local_manager.get_task(task_id)

    assert task is not None
    assert task["task_id"] == task_id
    assert task["title"] == "Analyser E-ZZIO"
    assert task["workspace"] == r"G:\AI\E-zzio"
    assert task["state"] == "DRAFT"
    assert task["scope"] == {"mode": "read_only"}
    assert task["plan"] == {"steps": ["inventory", "report"]}


def test_schema_validation_fails_on_wrong_schema(monkeypatch, tmp_path: Path):
    db_path = tmp_path / "bad_tasks.db"

    with sqlite3.connect(db_path) as conn:
        conn.execute("CREATE TABLE governed_tasks (task_id TEXT PRIMARY KEY)")

    monkeypatch.setattr(manager, "DB_PATH", db_path)

    with pytest.raises(RuntimeError, match="colonnes absentes"):
        manager.TaskManager()


def test_valid_task_transitions_require_approval(monkeypatch, tmp_path: Path):
    local_manager = make_manager(monkeypatch, tmp_path, "tasks_transition.db")
    task_id = create_draft(local_manager, "task_transition_001")

    assert local_manager.transition_task(task_id, "SCOPED")["state"] == "SCOPED"
    assert local_manager.transition_task(task_id, "PLANNED")["state"] == "PLANNED"
    assert local_manager.transition_task(task_id, "POLICY_CHECKED")["state"] == "POLICY_CHECKED"
    assert local_manager.transition_task(task_id, "AWAITING_APPROVAL")["state"] == "AWAITING_APPROVAL"

    with pytest.raises(PermissionError, match="approval_id obligatoire"):
        local_manager.transition_task(task_id, "RUNNING")

    running = local_manager.transition_task(
        task_id,
        "RUNNING",
        approval_id="approval_test_001",
    )

    assert running["state"] == "RUNNING"
    assert running["approval_id"] == "approval_test_001"


def test_invalid_task_transition_is_rejected(monkeypatch, tmp_path: Path):
    local_manager = make_manager(monkeypatch, tmp_path, "tasks_invalid.db")
    task_id = create_draft(local_manager, "task_transition_002")

    with pytest.raises(ValueError, match="Transition refusée"):
        local_manager.transition_task(task_id, "RUNNING")


def test_terminal_state_cannot_restart(monkeypatch, tmp_path: Path):
    local_manager = make_manager(monkeypatch, tmp_path, "tasks_terminal.db")
    task_id = create_draft(local_manager, "task_transition_003")

    local_manager.transition_task(task_id, "SCOPED")
    local_manager.transition_task(task_id, "PLANNED")
    local_manager.transition_task(task_id, "POLICY_CHECKED")
    local_manager.transition_task(task_id, "RUNNING")

    local_manager.transition_task(task_id, "VERIFYING")
    finished = local_manager.transition_task(task_id, "SUCCEEDED")

    assert finished["state"] == "SUCCEEDED"

    with pytest.raises(ValueError, match="Transition refusée"):
        local_manager.transition_task(task_id, "RUNNING")
