import pytest
from v17.concurrency.models import UnifiedChannelMessage, TaskPriority
from v17.concurrency.manager import concurrent_task_manager

def test_v17_7_multi_channel_submission():
    channels = ["webui", "discord", "voice", "api"]
    for ch in channels:
        msg = UnifiedChannelMessage(
            channel=ch,
            user_id=f"user_{ch}",
            session_id=f"session_{ch}",
            message_id=f"msg_{ch}",
            content="Bonjour E-ZZIO"
        )
        task = concurrent_task_manager.submit_task(msg)
        assert task.channel == ch
        assert task.status.value == "COMPLETED"
        assert task.verification == "PASS"
