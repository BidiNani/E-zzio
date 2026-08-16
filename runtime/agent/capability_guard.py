from enum import Enum
from .capability.registry import CapabilityRegistry

class CapabilityResult(str, Enum):
    VALID = "VALID"
    INVALID = "INVALID"

class CapabilityGuard:
    def __init__(self):
        self.registry = CapabilityRegistry()

    def validate(self, capability: str) -> CapabilityResult:
        # Validation dynamique basée sur les capacités enregistrées
        if self.registry.get(capability):
            return CapabilityResult.VALID
        return CapabilityResult.INVALID