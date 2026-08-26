from pydantic import BaseModel, Field
from typing import Dict, Any, List, Optional
from v17.read_model.models import (
    SystemOverviewDTO, ModelStatusDTO, TaskItemDTO,
    MemorySummaryDTO, ChannelsStatusDTO, OperationsDTO
)

class ProductStateSnapshot(BaseModel):
    schema_version: str = "17.2.0"
    generated_at: str
    system: SystemOverviewDTO
    models: ModelStatusDTO
    tasks: List[TaskItemDTO]
    memory: MemorySummaryDTO
    channels: ChannelsStatusDTO
    operations: OperationsDTO
    security_verdict: str = "FAIL_CLOSED_PROTECTED"
