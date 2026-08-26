import time
from enum import Enum
from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field

class TaskPriority(str, Enum):
    CRITICAL = "CRITICAL"
    HIGH = "HIGH"
    NORMAL = "NORMAL"
    LOW = "LOW"
    BACKGROUND = "BACKGROUND"

class TaskLifecycleStatus(str, Enum):
    CREATED = "CREATED"
    QUEUED = "QUEUED"
    PLANNING = "PLANNING"
    ROUTING = "ROUTING"
    RUNNING = "RUNNING"
    VERIFYING = "VERIFYING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"
    BLOCKED = "BLOCKED"

class UnifiedChannelMessage(BaseModel):
    channel: str # "webui", "discord", "voice", "api"
    user_id: str
    session_id: str
    message_id: str
    content: str
    timestamp: float = Field(default_factory=time.time)
    metadata: Dict[str, Any] = Field(default_factory=dict)

class ConcurrentTaskRecord(BaseModel):
    task_id: str
    session_id: str
    channel: str
    user_id: str
    priority: TaskPriority = TaskPriority.NORMAL
    status: TaskLifecycleStatus = TaskLifecycleStatus.CREATED
    intent: Optional[str] = None
    task_type: Optional[str] = None
    selected_model: Optional[str] = None
    provider: Optional[str] = None
    fallback_model: Optional[str] = None
    model_score: Optional[float] = None
    progress: float = 0.0
    created_at: float = Field(default_factory=time.time)
    started_at: Optional[float] = None
    completed_at: Optional[float] = None
    result: Optional[str] = None
    verification: str = "PENDING"
    error: Optional[str] = None
