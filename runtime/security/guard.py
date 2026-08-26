from typing import NamedTuple
from runtime.security.permissions import SecurityPolicy

class GuardDecision(NamedTuple):
    allowed: bool
    reason: str

class SecurityGuard:
    @classmethod
    def inspect(cls, tool_name: str, allowed_level: int = SecurityPolicy.LEVEL_READ) -> GuardDecision:
        level = SecurityPolicy.get_level(tool_name)
        if level > allowed_level:
            return GuardDecision(
                allowed=False,
                reason=f"Niveau requis ({level}) supérieur au niveau autorisé ({allowed_level})"
            )
        return GuardDecision(allowed=True, reason="Autorisé par la politique de sécurité.")
