"""Tests critiques pour core/tasks/manager.py."""
import pytest


@pytest.fixture
def temp_db(monkeypatch, tmp_path):
    from core.tasks import manager as mgr
    db = tmp_path / "tasks.db"
    monkeypatch.setattr(mgr, "DB_PATH", db, raising=False)
    return db


def test_task_manager_creates_table_on_init(temp_db):
    from core.tasks.manager import TaskManager
    TaskManager()
    assert temp_db.exists()


def test_task_manager_rejects_empty_task_id(temp_db):
    from core.tasks.manager import TaskManager
    tm = TaskManager()
    with pytest.raises(ValueError, match="task_id"):
        tm.create_task(task_id="", title="x", workspace="y", scope={})


def test_task_manager_rejects_empty_title(temp_db):
    from core.tasks.manager import TaskManager
    tm = TaskManager()
    with pytest.raises(ValueError, match="title"):
        tm.create_task(task_id="t1", title="", workspace="y", scope={})


def test_task_manager_rejects_empty_workspace(temp_db):
    from core.tasks.manager import TaskManager
    tm = TaskManager()
    with pytest.raises(ValueError, match="workspace"):
        tm.create_task(task_id="t1", title="x", workspace="", scope={})
