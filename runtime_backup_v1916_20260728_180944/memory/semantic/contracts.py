from dataclasses import dataclass, field, asdict
from typing import List, Dict, Any, Optional
from datetime import datetime
from enum import Enum

class SemanticSource(str, Enum):
    KERNEL = "kernel"
    DREAM = "dream"
    AGENT = "agent"

class SemanticIntent(str, Enum):
    RECALL = "recall"
    REASON = "reason"
    COMPARE = "compare"
    LEARN = "learn"

class MemoryType(str, Enum):
    EPISODE = "episode"
    RULE = "rule"
    FACT = "fact"
    BELIEF = "belief"

@dataclass
class SemanticFilters:
    memory_type: List[MemoryType] = field(default_factory=lambda: [MemoryType.EPISODE, MemoryType.RULE, MemoryType.FACT, MemoryType.BELIEF])
    confidence_min: float = 0.0
    session_id: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "memory_type": [t.value if isinstance(t, MemoryType) else t for t in self.memory_type],
            "confidence_min": self.confidence_min,
            "session_id": self.session_id
        }

@dataclass
class SemanticQuery:
    query_id: str
    source: SemanticSource
    intent: SemanticIntent
    text: str
    filters: SemanticFilters = field(default_factory=SemanticFilters)
    top_k: int = 5
    contract_version: str = "1.0"
    timestamp: int = field(default_factory=lambda: int(__import__('datetime').datetime.now(__import__('datetime').timezone.utc).timestamp()))

    def to_dict(self) -> Dict[str, Any]:
        return {
            "query_id": self.query_id,
            "source": self.source.value if isinstance(self.source, SemanticSource) else self.source,
            "intent": self.intent.value if isinstance(self.intent, SemanticIntent) else self.intent,
            "text": self.text,
            "filters": self.filters.to_dict(),
            "top_k": self.top_k,
            "contract_version": self.contract_version,
            "timestamp": self.timestamp
        }

@dataclass
class SemanticResultItem:
    memory_id: str
    type: MemoryType
    score: float
    content: str
    source: str = "sqlite"
    embedding_version: str = "1.0"
    embedding_dimension: Optional[int] = None
    content_hash: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        d["type"] = self.type.value if isinstance(self.type, MemoryType) else self.type
        return d

@dataclass
class SemanticQueryResult:
    query_id: str
    results: List[SemanticResultItem] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=lambda: {"retriever": "semantic_v1", "latency_ms": 0})
    contract_version: str = "1.0"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "query_id": self.query_id,
            "results": [r.to_dict() for r in self.results],
            "metadata": self.metadata,
            "contract_version": self.contract_version
        }