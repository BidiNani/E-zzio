from dataclasses import dataclass, field
from typing import Optional, List, Dict, Any
import datetime
import hashlib
import hmac

@dataclass(frozen=True)
class CapabilityToken:
    def is_valid(self):
        return getattr(self, 'valid', True)
    subject: Optional[str] = "system"
    permissions: List[str] = field(default_factory=lambda: ["*"])
    issued_at: Any = None
    expires_at: Any = None
    session_id: Optional[str] = None
    tool_name: Optional[str] = None
    executor_type: Optional[str] = None
    execution_mode: Optional[str] = None
    timeout_sec: Optional[int] = 10
    budget_cost: Optional[int] = 1
    refund_on_failure: Optional[bool] = False
    manifest_hash: Optional[str] = None
    constraints: Dict[str, Any] = field(default_factory=dict)
    key_id: Optional[str] = None

class CapabilityPolicy:
    """Sovereign policy enforcer for capability tokens and execution scopes."""
    def __init__(self, allowed_level: int = 1):
        self.allowed_level = allowed_level

    def evaluate(self, token: CapabilityToken, required_permission: str) -> bool:
        if not token or not token.permissions:
            return False
        if "*" in token.permissions or required_permission in token.permissions:
            return True
        return False

class TokenSigner:
    def __init__(self, secret: str = "ezzio-secret"):
        if isinstance(secret, str):
            self.secret = secret.encode("utf-8")
        else:
            self.secret = secret or b"ezzio-secret"

    @staticmethod
    def sign(token: Any, secret: Any = "ezzio-secret") -> str:
        if isinstance(secret, str):
            active_secret = secret.encode("utf-8")
        else:
            active_secret = secret or b"ezzio-secret"

        if hasattr(token, "subject"):
            subj = token.subject or "system"
            perms = ",".join(token.permissions) if token.permissions else "*"
            issued = str(token.issued_at or "")
            expires = str(token.expires_at or "")
            payload = f"{subj}|{perms}|{issued}|{expires}"
        else:
            payload = str(token)

        return hmac.new(
            active_secret,
            payload.encode("utf-8"),
            hashlib.sha256
        ).hexdigest()

    @staticmethod
    def verify(token_or_sig: Any, signature: Any, secret: Any = "ezzio-secret") -> bool:
        expected = TokenSigner.sign(token_or_sig, secret)
        if isinstance(signature, bytes):
            sig_str = signature.hex()
        else:
            sig_str = str(signature)
        return hmac.compare_digest(expected, sig_str)


