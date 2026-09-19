import uuid
from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import StrEnum
from typing import Any


class TaskState(StrEnum):
    DRAFT = "DRAFT"
    SCOPED = "SCOPED"
    PLANNED = "PLANNED"
    AWAITING_APPROVAL = "AWAITING_APPROVAL"
    EXECUTING = "EXECUTING"
    VERIFYING = "VERIFYING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"


ALLOWED_TRANSITIONS: dict[TaskState, list[TaskState]] = {
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
    scope: dict[str, Any] = field(default_factory=dict)
    plan: list[dict[str, Any]] = field(default_factory=list)
    approval_id: str | None = None
    error_message: str | None = None
    created_at: str = field(default_factory=lambda: datetime.now(UTC).isoformat())
    updated_at: str = field(default_factory=lambda: datetime.now(UTC).isoformat())

    def transition_to(self, new_state: TaskState) -> None:
        if new_state not in ALLOWED_TRANSITIONS.get(self.state, []):
            raise InvalidStateTransitionError(f"Transition interdite : {self.state.value} -> {new_state.value}")
        self.state = new_state
        self.updated_at = datetime.now(UTC).isoformat()
