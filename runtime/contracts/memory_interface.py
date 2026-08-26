from abc import ABC, abstractmethod


class MemoryInterface(ABC):
    @abstractmethod
    def store(self, key, value):
        pass

    @abstractmethod
    def retrieve(self, key):
        pass
