from .sandbox_exec import SandboxExecutePython
from .embedder import EmbedderCapability


class CapabilityRegistry:
    def __init__(self):
        self._capabilities = {}
        self.register(SandboxExecutePython)
        self.register(EmbedderCapability)

    def register(self, capability_class):
        instance = capability_class()
        self._capabilities[instance.name] = instance

    def get(self, name):
        return self._capabilities.get(name)
