import pytest
import threading
from v17.concurrency.models import UnifiedChannelMessage, TaskPriority
from v17.concurrency.manager import concurrent_task_manager

def test_v17_7_concurrent_10_tasks():
    results = []
    threads = []

    def worker(i):
        msg = UnifiedChannelMessage(
            channel="webui" if i % 2 == 0 else "discord",
            user_id=f"user_{i}",
            session_id=f"sess_{i}",
            message_id=f"m_{i}",
            content="Analyse ce script powershell" if i % 3 == 0 else "Bonjour"
        )
        task = concurrent_task_manager.submit_task(msg)
        results.append(task)

    for i in range(10):
        t = threading.Thread(target=worker, args=(i,))
        threads.append(t)
        t.start()

    for t in threads:
        t.join()

    assert len(results) == 10
    for r in results:
        assert r.status.value == "COMPLETED"
        assert r.selected_model is not None
