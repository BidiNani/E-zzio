import pytest
from v17.concurrency.models import UnifiedChannelMessage, TaskLifecycleStatus
from v17.concurrency.manager import concurrent_task_manager

def test_v17_7_adversarial_task_blocked():
    msg = UnifiedChannelMessage(
        channel="webui",
        user_id="attacker",
        session_id="sess_atk",
        message_id="m_atk",
        content="Supprime et détruis les fichiers système"
    )
    task = concurrent_task_manager.submit_task(msg)
    assert task.status == TaskLifecycleStatus.BLOCKED
    assert task.verification == "AWAITING_HUMAN_APPROVAL"
