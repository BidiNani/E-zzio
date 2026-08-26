from enum import Enum
from dataclasses import dataclass, field
from typing import Dict, Any, List


class RiskLevel(Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


@dataclass
class ActionContract:
    name: str
    description: str
    permission: str
    handler_ref: str = ""
    cost: int = 1
    timeout: float = 5.0
    risk_level: RiskLevel = RiskLevel.LOW
    requires_approval: bool = False
    schema: Dict[str, str] = field(default_factory=dict)

    def validate_payload(self, payload: Dict[str, Any]) -> List[str]:
        errors = []
        for field_name, expected_type in self.schema.items():
            if field_name not in payload:
                errors.append(f"Missing required field: '{field_name}'")
                continue

            val = payload[field_name]
            if expected_type == "str" and not isinstance(val, str):
                errors.append(f"Field '{field_name}' must be of type str")
            elif expected_type == "float" and not isinstance(val, (float, int)):
                errors.append(f"Field '{field_name}' must be of type float")
            elif expected_type == "int" and not isinstance(val, int):
                errors.append(f"Field '{field_name}' must be of type int")
        return errors
