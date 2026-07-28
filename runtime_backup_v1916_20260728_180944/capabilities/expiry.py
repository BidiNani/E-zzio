from datetime import datetime, timezone
from typing import Dict, Any

class CapabilityExpiryManager:
    @staticmethod
    def check_expiry(token_meta: Dict[str, Any]) -> bool:
        """
        Verifies capability token expiry against UTC timestamp.
        Supports Unix epoch floats/ints, ISO strings, or datetime objects.
        """
        expires_at = token_meta.get("expires_at")
        if expires_at is None:
            return False

        now = datetime.now(timezone.utc).timestamp()

        if isinstance(expires_at, (int, float)):
            return now > float(expires_at)
        elif isinstance(expires_at, str):
            try:
                dt = datetime.fromisoformat(expires_at)
                if dt.tzinfo is None:
                    dt = dt.replace(tzinfo=timezone.utc)
                return now > dt.timestamp()
            except ValueError:
                return True
        elif isinstance(expires_at, datetime):
            dt = expires_at
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            return now > dt.timestamp()

        return False
