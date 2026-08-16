from abc import ABC, abstractmethod

class CognitionInterface(ABC):

    @abstractmethod
    def process(self, request):
        pass
