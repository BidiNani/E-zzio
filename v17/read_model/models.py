from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional

class SystemOverviewDTO(BaseModel):
    version: str
    environment: str
    readiness: str
    guardian_status: str
    security_status: str
    timestamp: str

class ModelStatusDTO(BaseModel):
    active_model: str
    provider: str
    capabilities: List[str]
    status: str

class TaskItemDTO(BaseModel):
    task_id: str
    objective: str
    status: str
    progress: float
    created_at: str

class MemorySummaryDTO(BaseModel):
    total_sessions: int
    total_messages: int
    fts5_active: bool
    recent_sessions: List[str]

class ResearchItemDTO(BaseModel):
    query: str
    provider: str
    facts_count: int
    verified: bool

class EvidenceItemDTO(BaseModel):
    evidence_id: str
    task_id: str
    provider: str
    verified: bool

class ChannelsStatusDTO(BaseModel):
    discord_status: str
    voice_status: str
    open_webui_status: str
    tailscale_serve_url: str

class OperationsDTO(BaseModel):
    watchdog_status: str
    last_backup: str
    recovery_ready: bool
    process_ram_mb: float

class ProductOverviewDTO(BaseModel):
    system: SystemOverviewDTO
    models: ModelStatusDTO
    tasks_count: int
    memory: MemorySummaryDTO
    channels: ChannelsStatusDTO
    operations: OperationsDTO
