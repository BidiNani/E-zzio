from dataclasses import dataclass, field
from typing import Optional, Any

@dataclass
class BrainRequest:
    request_id: str
    text: str
    provider_override: Optional[str] = None
    history_context: Optional[list] = None

@dataclass
class BrainResponseChunk:
    request_id: str
    chunk_text: str
    is_final: bool = False
    status: str = "GENERATING"  # "GENERATING", "COMPLETED", "INTERRUPTED"
    metadata: dict = field(default_factory=dict)
