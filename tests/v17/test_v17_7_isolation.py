import pytest
from v17.concurrency.models import UnifiedChannelMessage
from v17.concurrency.manager import concurrent_task_manager

def test_v17_7_task_and_session_isolation():
    msg1 = UnifiedChannelMessage(channel="discord", user_id="alice", session_id="sess_alice", message_id="m1", content="Secret Alice")
    msg2 = UnifiedChannelMessage(channel="webui", user_id="bob", session_id="sess_bob", message_id="m2", content="Secret Bob")
    
    t1 = concurrent_task_manager.submit_task(msg1)
    t2 = concurrent_task_manager.submit_task(msg2)
    
    assert t1.task_id != t2.task_id
    assert t1.session_id != t2.session_id
    assert t1.user_id != t2.user_id
