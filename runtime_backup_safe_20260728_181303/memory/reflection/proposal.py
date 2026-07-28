from dataclasses import dataclass, field, asdict
from typing import List
from datetime import datetime

@dataclass
class ReflectionProposal:
    proposal_id: str
    type: str # 'fact_candidate', 'belief_update', 'skill_candidate', 'rule_candidate'
    statement: str
    confidence: float
    evidence: List[str]
    status: str = "PENDING"
    created_at: str = field(default_factory=lambda: __import__('datetime').datetime.now(__import__('datetime').timezone.utc).isoformat())
    validated_at: str = None

    def to_dict(self):
        return asdict(self)