import pytest
from v17.concurrency.manager import concurrent_task_manager

def test_v17_7_task_retrieval_and_integrity():
    tasks = concurrent_task_manager.list_tasks(limit=10)
    assert isinstance(tasks, list)
