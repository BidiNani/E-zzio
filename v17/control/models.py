from enum import Enum
from pydantic import BaseModel, Field
from typing import Dict, Any, Optional

class RiskLevel(str, Enum):
    READ_ONLY = "READ_ONLY"
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"

class ActionStatus(str, Enum):
    CREATED = "CREATED"
    CLASSIFIED = "CLASSIFIED"
    AWAITING_CONFIRMATION = "AWAITING_CONFIRMATION"
    APPROVED = "APPROVED"
    DENIED = "DENIED"
    DISPATCHED = "DISPATCHED"
    RUNNING = "RUNNING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"
    EXPIRED = "EXPIRED"
    VERIFIED = "VERIFIED"

class ActionRequest(BaseModel):
    request_id: str
    session_id: str
    actor: str = "human_operator"
    action_type: str
    target: str
    parameters: Dict[str, Any] = Field(default_factory=dict)
    risk_level: RiskLevel = RiskLevel.READ_ONLY
    created_at: str
    expires_at: str
    confirmation_required: bool = False
    idempotency_key: Optional[str] = None
    status: ActionStatus = ActionStatus.CREATED
    result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
