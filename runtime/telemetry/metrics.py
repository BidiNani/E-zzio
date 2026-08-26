from dataclasses import dataclass, field
from typing import Optional
import socket
import threading


@dataclass
class ExecutionMetric:
    """Métrique d'exécution distribuée OpenTelemetry-compatible."""

    exec_id: str
    action_name: str
    status: str
    duration_ms: float
    cost: float
    risk_level: str
    category: Optional[str] = None

    # Traçabilité OpenTelemetry
    trace_id: Optional[str] = None
    span_id: Optional[str] = None
    parent_span_id: Optional[str] = None
    session_id: Optional[str] = None
    error_stack_hash: Optional[str] = None

    # Métadonnées système & charges
    payload_size_bytes: int = 0
    thread_id: int = field(default_factory=threading.get_ident)
    hostname: str = field(default_factory=socket.gethostname)
