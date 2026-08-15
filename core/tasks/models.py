from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional
import uuid

class TaskState(str, Enum):
    DRAFT = "DRAFT"
    SCOPED = "SCOPED"
    PLANNED = "PLANNED"
    AWAITING_APPROVAL = "AWAITING_APPROVAL"
    EXECUTING = "EXECUTING"
    VERIFYING = "VERIFYING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"

ALLOWED_TRANSITIONS: Dict[TaskState, List[TaskState]] = {
    TaskState.DRAFT: [TaskState.SCOPED, TaskState.CANCELLED],
    TaskState.SCOPED: [TaskState.PLANNED, TaskState.CANCELLED],
    TaskState.PLANNED: [TaskState.AWAITING_APPROVAL, TaskState.CANCELLED],
    TaskState.AWAITING_APPROVAL: [TaskState.EXECUTING, TaskState.CANCELLED],
    TaskState.EXECUTING: [TaskState.VERIFYING, TaskState.FAILED, TaskState.CANCELLED],
    TaskState.VERIFYING: [TaskState.COMPLETED, TaskState.FAILED, TaskState.CANCELLED],
    TaskState.FAILED: [TaskState.PLANNED, TaskState.CANCELLED],
    TaskState.COMPLETED: [],
    TaskState.CANCELLED: [],
}

class InvalidStateTransitionError(Exception):
    pass

@dataclass
class Task:
    title: str
    workspace: str
    task_id: str = field(default_factory=lambda: f"tsk_{uuid.uuid4().hex[:12]}")
    state: TaskState = TaskState.DRAFT
    scope: Dict[str, Any] = field(default_factory=dict)
    plan: List[Dict[str, Any]] = field(default_factory=list)
    approval_id: Optional[str] = None
    error_message: Optional[str] = None
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    updated_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    def transition_to(self, new_state: TaskState) -> None:
        if new_state not in ALLOWED_TRANSITIONS.get(self.state, []):
            raise InvalidStateTransitionError(
                f"Transition interdite : {self.state.value} -> {new_state.value}"
            )
        self.state = new_state
        self.updated_at = datetime.now(timezone.utc).isoformat()
