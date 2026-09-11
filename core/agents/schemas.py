"""E-ZZIO — schémas Pydantic stricts inter-agents (zéro texte libre)."""
from __future__ import annotations

from datetime import datetime, timezone
from typing import List, Literal, Optional

from pydantic import BaseModel, Field


class AgentContribution(BaseModel):
    agent_id: str
    phase: Literal["PROPOSAL", "CRITIQUE", "SYNTHESIS"]
    confidence: float = Field(ge=0.0, le=1.0)
    summary: str = Field(max_length=200, description="Synthese ultra-dense sans fioritures")
    unified_diff: Optional[str] = Field(default=None, description="Patch unifie si modification de code")
    identified_risks: List[str] = Field(default_factory=list, max_items=5)
    blockers: List[str] = Field(default_factory=list, max_items=3)

    model_config = {"extra": "forbid"}


class ADRRecord(BaseModel):
    adr_id: str
    title: str = Field(max_length=120)
    decision: str = Field(max_length=2000)
    rationale: str = Field(max_length=2000)
    rejected_alternatives: List[str] = Field(default_factory=list, max_items=5)
    status: Literal["PROPOSED", "ACCEPTED", "SUPERSEDED"] = "PROPOSED"
    decided_by: str = "ezzio-master"
    decided_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    model_config = {"extra": "forbid"}
