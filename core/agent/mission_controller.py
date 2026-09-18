"""
core/agent/mission_controller.py — Mission Controller & Task Management Gateways
"""
from __future__ import annotations

import enum
from dataclasses import dataclass, field
from typing import Any


class MissionStatus(str, enum.Enum):
    QUEUED = "QUEUED"
    RUNNING = "RUNNING"
    SUCCEEDED = "SUCCEEDED"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"
    PAUSED = "PAUSED"
    UNKNOWN = "UNKNOWN"


class TaskStatus(str, enum.Enum):
    CREATED = "CREATED"
    QUEUED = "QUEUED"
    RUNNING = "RUNNING"
    PAUSING = "PAUSING"
    PAUSED = "PAUSED"
    RESUMING = "RESUMING"
    CANCELLING = "CANCELLING"
    CANCELLED = "CANCELLED"
    SUCCEEDED = "SUCCEEDED"
    FAILED = "FAILED"
    UNKNOWN = "UNKNOWN"


class WorkerRole(str, enum.Enum):
    CODER = "CODER"
    RESEARCHER = "RESEARCHER"
    QA = "QA"
    SECURITY = "SECURITY"
    MASTER = "MASTER"


@dataclass
class MissionRecord:
    mission_id: str
    goal: str
    worker_type: str = "CODER_WORKER"
    status: MissionStatus = MissionStatus.QUEUED
    request_id: str = ""
    model: str = ""
    provider: str = ""
    result: dict[str, Any] = field(default_factory=dict)
    created_at: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.mission_id,
            "mission_id": self.mission_id,
            "title": self.goal,
            "name": self.goal,
            "description": self.goal,
            "worker_type": self.worker_type,
            "status": self.status.value if hasattr(self.status, "value") else str(self.status),
            "request_id": self.request_id,
            "model": self.model,
            "provider": self.provider,
            "result": self.result,
            "created_at": self.created_at,
            "createdAt": self.created_at,
            "tasks": [],
        }


@dataclass
class MissionTask:
    task_id: str
    title: str
    description: str
    role: WorkerRole = WorkerRole.CODER
    status: TaskStatus = TaskStatus.CREATED

    def transition_to(self, new_status: TaskStatus | str) -> bool:
        if isinstance(new_status, str):
            try:
                new_status = TaskStatus(new_status)
            except ValueError:
                return False
        self.status = new_status
        return True


@dataclass
class TaskGraph:
    nodes: dict[str, MissionTask] = field(default_factory=dict)


class MissionRegistry:
    def __init__(self):
        self._missions: dict[str, MissionRecord] = {}

    def register(self, record: MissionRecord) -> None:
        self._missions[record.mission_id] = record

    def get(self, mission_id: str) -> MissionRecord | None:
        return self._missions.get(mission_id)

    def list_all(self) -> list[MissionRecord]:
        return list(self._missions.values())

    def cancel(self, mission_id: str) -> bool:
        m = self._missions.get(mission_id)
        if not m:
            return False
        m.status = MissionStatus.CANCELLED
        return True

    def pause(self, mission_id: str) -> bool:
        m = self._missions.get(mission_id)
        if not m:
            return False
        m.status = MissionStatus.PAUSED
        return True

    def resume(self, mission_id: str) -> bool:
        m = self._missions.get(mission_id)
        if not m:
            return False
        m.status = MissionStatus.RUNNING
        return True


mission_registry = MissionRegistry()


class MissionController:
    def __init__(self, *args, **kwargs):
        pass


mission_controller = MissionController()
