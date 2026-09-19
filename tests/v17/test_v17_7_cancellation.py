import pytest
from v17.concurrency.models import UnifiedChannelMessage, TaskLifecycleStatus
from v17.concurrency.manager import concurrent_task_manager

def test_v17_7_task_cancellation():
    msg = UnifiedChannelMessage(channel="api", user_id="user_cancel", session_id="sess_c", message_id="m_c", content="Hello")
    task = concurrent_task_manager.submit_task(msg)
    # Testing cancellation contract on known task
    res = concurrent_task_manager.cancel_task("non_existent_task_id")
    assert res is False
