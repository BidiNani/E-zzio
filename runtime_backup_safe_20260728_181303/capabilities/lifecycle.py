from enum import Enum

class CapabilityState(str, Enum):
    ISSUED = "ISSUED"
    ACTIVE = "ACTIVE"
    USED = "USED"
    EXPIRED = "EXPIRED"
    REVOKED = "REVOKED"
