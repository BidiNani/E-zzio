from datetime import datetime, timezone
from runtime.capabilities.lifecycle import CapabilityState

class CapabilityExpiryManager:
    """
    Evaluates token lifetime against absolute timeouts.
    """
    @staticmethod
    def check_expiry(token_meta: dict) -> bool:
        expires_at = token_meta.get("expires_at")
        if not expires_at:
            return False
        return datetime.now(timezone.utc) > expires_at
