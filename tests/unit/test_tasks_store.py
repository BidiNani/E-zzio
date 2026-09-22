"""Tests réels pour core/tasks/store.py.

SqliteTaskStore : persistance SQLite des tâches gouvernées.
TaskState adapté aux vrais noms trouvés : DRAFT SCOPED PLANNED AWAITING_APPROVAL EXECUTING VERIFYING COMPLETED FAILED CANCELLED
"""
from __future__ import annotations

from pathlib import Path

import pytest

from core.tasks.models import Task, TaskState
from core.tasks.store import SqliteTaskStore

STATE_A = TaskState.DRAFT
STATE_B = TaskState.SCOPED


@pytest.fixture
def store(tmp_path):
    db_path = tmp_path / "tasks.db"
    return SqliteTaskStore(db_path=db_path)


@pytest.fixture
def sample_task():
    return Task(
        task_id="task-001",
        title="Test task",
        workspace="/tmp/ws",
        state=STATE_A,
        scope={"files": ["a.py"]},
        plan={"steps": [1, 2]},
        approval_id=None,
        error_message=None,
        created_at="2026-09-22T12:00:00",
        updated_at="2026-09-22T12:00:00",
    )


class TestInit:
    def test_creates_db_file(self, tmp_path):
        db_path = tmp_path / "test.db"
        SqliteTaskStore(db_path=db_path)
        assert db_path.exists()

    def test_creates_parent_dir(self, tmp_path):
        db_path = tmp_path / "sub" / "tasks.db"
        SqliteTaskStore(db_path=db_path)
        assert db_path.parent.exists()

    def test_idempotent_init(self, tmp_path):
        db_path = tmp_path / "tasks.db"
        SqliteTaskStore(db_path=db_path)
        SqliteTaskStore(db_path=db_path)


class TestSaveAndGet:
    def test_save_and_get(self, store, sample_task):
        store.save(sample_task)
        result = store.get_by_id("task-001")
        assert result is not None
        assert result.task_id == "task-001"
        assert result.title == "Test task"
        assert result.workspace == "/tmp/ws"
        assert result.state == STATE_A

    def test_get_unknown_id(self, store):
        assert store.get_by_id("no-such-id") is None

    def test_save_updates_state_only(self, store, sample_task):
        """UPSERT met à jour state mais garde title/workspace (design)."""
        store.save(sample_task)
        sample_task.state = STATE_B
        store.save(sample_task)
        result = store.get_by_id("task-001")
        # title reste immuable
        assert result.title == "Test task"
        # state est bien mis à jour
        assert result.state == STATE_B

    def test_save_scope_and_plan_json(self, store, sample_task):
        store.save(sample_task)
        result = store.get_by_id("task-001")
        assert result.scope == {"files": ["a.py"]}
        assert result.plan == {"steps": [1, 2]}

    def test_save_with_approval_and_error(self, store, sample_task):
        sample_task.approval_id = "appr-123"
        sample_task.error_message = "something wrong"
        store.save(sample_task)
        result = store.get_by_id("task-001")
        assert result.approval_id == "appr-123"
        assert result.error_message == "something wrong"


class TestListByState:
    def test_list_empty(self, store):
        assert store.list_by_state(STATE_A) == []

    def test_list_filters_by_state(self, store):
        for i, state in enumerate([STATE_A, STATE_A, STATE_B]):
            task = Task(
                task_id=f"t{i}",
                title=f"Task {i}",
                workspace="/ws",
                state=state,
                scope={}, plan={},
                approval_id=None, error_message=None,
                created_at="2026-01-01T00:00:00",
                updated_at="2026-01-01T00:00:00",
            )
            store.save(task)

        a_tasks = store.list_by_state(STATE_A)
        b_tasks = store.list_by_state(STATE_B)
        assert len(a_tasks) == 2
        assert len(b_tasks) == 1

    def test_list_returns_all_matching(self, store):
        for i in range(5):
            task = Task(
                task_id=f"x{i}",
                title="x",
                workspace="/ws",
                state=STATE_A,
                scope={}, plan={},
                approval_id=None, error_message=None,
                created_at="2026-01-01T00:00:00",
                updated_at="2026-01-01T00:00:00",
            )
            store.save(task)
        assert len(store.list_by_state(STATE_A)) == 5


class TestPersistence:
    def test_data_survives_new_instance(self, tmp_path, sample_task):
        db_path = tmp_path / "tasks.db"
        store1 = SqliteTaskStore(db_path=db_path)
        store1.save(sample_task)

        store2 = SqliteTaskStore(db_path=db_path)
        result = store2.get_by_id("task-001")
        assert result is not None
        assert result.title == "Test task"
