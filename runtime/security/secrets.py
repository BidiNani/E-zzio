import os

class SecretKeyManager:
    def __init__(self, master_key: str = None):
        self.master_key = master_key or os.getenv("EZZIO_MASTER_KEY", "default-sovereign-key")

    def get_secret(self, key_name: str) -> str:
        return os.getenv(key_name, f"mock-secret-{key_name}")

class SecretProvider:
    def __init__(self):
        self.manager = SecretKeyManager()

    def resolve(self, key: str) -> str:
        return self.manager.get_secret(key)

secret_provider = SecretProvider()
