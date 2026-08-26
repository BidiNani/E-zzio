import hmac
import hashlib
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import FrozenSet, Optional, Dict, Union


@dataclass(frozen=True)
class CapabilityToken:
    """Token de capacite immuable autorisant une action."""

    subject: str
    permissions: FrozenSet[str]
    issued_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    expires_at: Optional[datetime] = None
    signature: Optional[str] = None

    def allows(self, permission: str) -> bool:
        if self.expires_at and datetime.now(timezone.utc) > self.expires_at:
            return False
        return permission in self.permissions


class TokenSigner:
    """Signateur et verificateur cryptographique de tokens de capacite."""

    def __init__(self, secret_key: Union[bytes, str] = b"ezzio-default-runtime-key"):
        if isinstance(secret_key, str):
            secret_key = secret_key.encode("utf-8")
        self._key = secret_key

    def sign(self, token: CapabilityToken) -> str:
        raw = f"{token.subject}:{sorted(list(token.permissions))}:{token.issued_at.isoformat()}"
        return hmac.new(self._key, raw.encode("utf-8"), hashlib.sha256).hexdigest()

    def verify(self, token: CapabilityToken) -> bool:
        if not token.signature:
            return False
        expected = self.sign(token)
        return hmac.compare_digest(expected, token.signature)


@dataclass
class CapabilityPolicy:
    """Politique de capacite associant des sujets a des permissions."""

    rules: Dict[str, FrozenSet[str]] = field(default_factory=dict)

    def get_permissions(self, subject: str) -> FrozenSet[str]:
        return self.rules.get(subject, frozenset())

    def is_valid(self):
        return getattr(self, "valid", True)
