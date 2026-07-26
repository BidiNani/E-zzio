from dataclasses import dataclass, field
from typing import List

@dataclass
class Capability:
    name: str
    permissions: List[str] = field(default_factory=list)
    enabled: bool = True

    def allows(self, permission: str) -> bool:
        return self.enabled and (permission in self.permissions or "*" in self.permissions)
