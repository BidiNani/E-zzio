from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, Any, List
import uuid
import time

class AgentStatus(str, Enum):
    CREATED = "CREATED"
    PLANNING = "PLANNING"
    WAITING_APPROVAL = "WAITING_APPROVAL"
    EXECUTING = "EXECUTING"
    VERIFYING = "VERIFYING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    HALTED = "HALTED"

@dataclass
class AgentTask:
    objective: str
    task_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    max_iterations: int = 2
    risk_level: str = "LOW"

@dataclass
class AgentStep:
    capability: str
    parameters: Dict[str, Any]
    step_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    reversible: bool = True

@dataclass
class AgentPlan:
    task_id: str
    steps: List[AgentStep]
    plan_id: str = field(default_factory=lambda: str(uuid.uuid4()))

@dataclass
class ExecutionResult:
    step_id: str
    status: str
    output: Dict[str, Any]
    timestamp: float = field(default_factory=time.time)

@dataclass
class VerificationResult:
    success: bool
    reason: str
    recoverable: bool = False