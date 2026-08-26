from abc import ABC, abstractmethod


class TelemetryInterface(ABC):
    @abstractmethod
    def emit(self, event):
        pass
