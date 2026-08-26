from runtime.capabilities.lifecycle import CapabilityState


class CapabilityValidator:
    """
    Validates capability token state and integrity.
    Rule: Revoked or expired tokens can never be active.
    """

    @staticmethod
    def is_valid(token_meta: dict) -> bool:
        state = token_meta.get("state")
        if state in (CapabilityState.EXPIRED, CapabilityState.REVOKED):
            return False
        return state in (CapabilityState.ISSUED, CapabilityState.ACTIVE)
