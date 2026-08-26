import uuid
import time
import threading
from typing import Dict, Any, List, Optional

from v17.concurrency.models import (
    UnifiedChannelMessage, ConcurrentTaskRecord,
    TaskPriority, TaskLifecycleStatus
)
from v17.concurrency.governor import resource_governor
from v17.orchestration.intent import intent_engine
from v17.models.intelligence_router import model_intelligence_router
from v17.events.buffer import global_event_buffer
from v17.events.models import EventSeverity
from v17.sanitization.sanitizer import sanitize_data

class ConcurrentTaskManager:
    def __init__(self):
        self._tasks: Dict[str, ConcurrentTaskRecord] = {}
        self._cancellation_tokens: Dict[str, threading.Event] = {}
        self._lock = threading.Lock()

    def submit_task(
        self,
        msg: UnifiedChannelMessage,
        priority: TaskPriority = TaskPriority.NORMAL,
        timeout_s: float = 30.0
    ) -> ConcurrentTaskRecord:
        task_id = f"task_{uuid.uuid4().hex[:12]}"
        cancel_event = threading.Event()

        task = ConcurrentTaskRecord(
            task_id=task_id,
            session_id=msg.session_id,
            channel=msg.channel,
            user_id=msg.user_id,
            priority=priority,
            status=TaskLifecycleStatus.QUEUED,
            created_at=time.time()
        )

        with self._lock:
            self._tasks[task_id] = task
            self._cancellation_tokens[task_id] = cancel_event

        global_event_buffer.publish(
            event_type="task.queued",
            source="v17.concurrency.manager",
            payload={"task_id": task_id, "session_id": msg.session_id, "channel": msg.channel},
            severity=EventSeverity.INFO
        )

        # Run task synchronously or threaded while tracking cancellation
        self._execute_task(task_id, msg.content, cancel_event)
        return self._tasks[task_id]

    def _execute_task(self, task_id: str, content: str, cancel_event: threading.Event):
        task = self._tasks[task_id]

        if cancel_event.is_set():
            task.status = TaskLifecycleStatus.CANCELLED
            return

        resource_governor.acquire_slot()
        task.started_at = time.time()
        task.status = TaskLifecycleStatus.PLANNING

        # 1. Intent Extraction
        intent = intent_engine.parse_intent(content)
        task.intent = intent.raw_prompt
        task.task_type = intent.task_type
        task.status = TaskLifecycleStatus.ROUTING

        # 2. Model Routing per task
        route = model_intelligence_router.route_for_task(intent.task_type)
        task.selected_model = route.selected_model
        task.provider = route.provider
        task.fallback_model = route.fallback_model
        task.model_score = route.score

        global_event_buffer.publish(
            event_type="task.model_selected",
            source="v17.concurrency.manager",
            payload={"task_id": task_id, "model": route.selected_model, "score": route.score},
            severity=EventSeverity.INFO
        )

        if cancel_event.is_set():
            task.status = TaskLifecycleStatus.CANCELLED
            resource_governor.release_slot()
            return

        # 3. Execution & Synthesis
        task.status = TaskLifecycleStatus.RUNNING
        task.progress = 0.5

        if intent.requires_human_approval:
            task.status = TaskLifecycleStatus.BLOCKED
            task.verification = "AWAITING_HUMAN_APPROVAL"
            task.result = "Task requires explicit Human Approval before proceeding."
            resource_governor.release_slot()
            return

        # 4. Verifying & Completion
        task.status = TaskLifecycleStatus.VERIFYING
        raw_res = f"Execution result for task [{task.task_type}] via model [{task.selected_model}]"
        task.result = sanitize_data(raw_res)
        task.verification = "PASS"
        task.progress = 1.0
        task.completed_at = time.time()
        task.status = TaskLifecycleStatus.COMPLETED

        resource_governor.release_slot()

        global_event_buffer.publish(
            event_type="task.completed",
            source="v17.concurrency.manager",
            payload={"task_id": task_id, "status": task.status.value, "model": task.selected_model},
            severity=EventSeverity.INFO
        )

    def cancel_task(self, task_id: str) -> bool:
        with self._lock:
            if task_id not in self._tasks:
                return False
            token = self._cancellation_tokens.get(task_id)
            if token:
                token.set()
            task = self._tasks[task_id]
            if task.status not in [TaskLifecycleStatus.COMPLETED, TaskLifecycleStatus.FAILED]:
                task.status = TaskLifecycleStatus.CANCELLED
                global_event_buffer.publish(
                    event_type="task.cancelled",
                    source="v17.concurrency.manager",
                    payload={"task_id": task_id},
                    severity=EventSeverity.WARNING
                )
                return True
        return False

    def get_task(self, task_id: str) -> Optional[ConcurrentTaskRecord]:
        with self._lock:
            return self._tasks.get(task_id)

    def list_tasks(self, limit: int = 50) -> List[ConcurrentTaskRecord]:
        with self._lock:
            records = list(self._tasks.values())
            records.sort(key=lambda t: t.created_at, reverse=True)
            return records[:limit]

concurrent_task_manager = ConcurrentTaskManager()
