import time
import uuid
from enum import Enum
from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field

class SubtaskState(str, Enum):
    PENDING = "PENDING"
    RUNNING = "RUNNING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"
    BLOCKED = "BLOCKED"

class SubtaskNode(BaseModel):
    subtask_id: str
    parent_mission_id: str
    role: str # "PLANNER", "RESEARCHER", "CODER", "ANALYST", "VERIFIER", "EXECUTOR"
    task_type: str
    dependencies: List[str] = Field(default_factory=list)
    assigned_model: Optional[str] = None
    state: SubtaskState = SubtaskState.PENDING
    result: Optional[str] = None
    evidence_id: Optional[str] = None

class MissionRecord(BaseModel):
    mission_id: str
    title: str
    session_id: str
    channel: str
    subtasks: List[SubtaskNode] = Field(default_factory=list)
    status: str = "IN_PROGRESS"
    created_at: float = Field(default_factory=time.time)
    completed_at: Optional[float] = None
