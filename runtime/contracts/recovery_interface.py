from abc import ABC, abstractmethod

class RecoveryInterface(ABC):

    @abstractmethod
    def recover(self):
        pass
