from enum import Enum
from pydantic import BaseModel, Field
from typing import Dict, Any, Optional

class EventSeverity(str, Enum):
    INFO = "INFO"
    NOTICE = "NOTICE"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"

class ProductEvent(BaseModel):
    event_id: str
    event_type: str
    schema_version: str = "17.2.0"
    timestamp: str
    source: str
    severity: EventSeverity = EventSeverity.INFO
    correlation_id: Optional[str] = None
    payload: Dict[str, Any] = Field(default_factory=dict)
