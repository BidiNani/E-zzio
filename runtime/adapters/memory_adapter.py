from runtime.contracts.memory_interface import MemoryInterface


class MemoryAdapter(MemoryInterface):
    def store(self, key, value):
        raise NotImplementedError("Runtime implementation required")

    def retrieve(self, key):
        raise NotImplementedError("Runtime implementation required")
