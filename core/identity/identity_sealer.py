import hashlib
import hmac
import os

from dotenv import load_dotenv

from core.identity.canonical_identity import CanonicalIdentity

load_dotenv()


class IdentitySealer:
    def __init__(self):
        self.secret = os.getenv("EZZIO_LEDGER_SECRET", "").encode("utf-8")
        self.identity = CanonicalIdentity()

    def seal(self) -> dict:
        """Signe l'identité courante avec le secret maître."""
        payload = self.identity.get_canonical_json()
        payload_hash = hashlib.sha256(payload.encode("utf-8")).hexdigest()

        signature = hmac.new(self.secret, payload.encode("utf-8"), hashlib.sha256).hexdigest()

        return {"identity": self.identity.get_payload(), "hash": payload_hash, "signature": signature}
