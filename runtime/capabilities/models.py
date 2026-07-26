from dataclasses import dataclass, field
from typing import List

@dataclass(frozen=True)
class CapabilityToken:
    id: str
    issuer: str
    subject: str
    permissions: List[str]
    expires_at: float
    signature: str
