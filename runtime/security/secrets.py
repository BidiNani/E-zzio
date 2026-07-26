import os
import secrets

class SecretKeyManager:
    """Gestionnaire de clé cryptographique avec identification (pour audit et rotation)."""
    def __init__(self):
        env_key = os.environ.get("EZZIO_HMAC_SECRET")
        if env_key:
            self._key = env_key.encode("utf-8")
            self.key_id = os.environ.get("EZZIO_KEY_ID", "env-key")
        else:
            self._key = secrets.token_bytes(32)
            self.key_id = "ephemeral-key"

    def get_key(self) -> bytes:
        return self._key