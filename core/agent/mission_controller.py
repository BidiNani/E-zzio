"""
core/agent/mission_controller.py — Mission Controller & Task Management Gateways
"""
from __future__ import annotations

import enum
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


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
    result: Dict[str, Any] = field(default_factory=dict)
    created_at: str = ""


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
    nodes: Dict[str, MissionTask] = field(default_factory=dict)


class MissionRegistry:
    def __init__(self):
        self._missions: Dict[str, MissionRecord] = {}

    def register(self, record: MissionRecord) -> None:
        self._missions[record.mission_id] = record

    def get(self, mission_id: str) -> Optional[MissionRecord]:
        return self._missions.get(mission_id)

    def list_all(self) -> List[MissionRecord]:
        return list(self._missions.values())


mission_registry = MissionRegistry()


class MissionController:
    def __init__(self, *args, **kwargs):
        pass


mission_controller = MissionController()
