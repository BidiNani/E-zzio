from dataclasses import dataclass, field
from typing import List
import time

@dataclass(frozen=True)
class CapabilityToken:
    id: str
    issuer: str
    subject: str
    permissions: List[str]
    expires_at: float
    signature: str

    def is_expired(self) -> bool:
        return time.time() > self.expires_at

    def allows(self, permission: str) -> bool:
        return permission in self.permissions
