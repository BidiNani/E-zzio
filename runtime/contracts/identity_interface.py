from abc import ABC, abstractmethod

class IdentityInterface(ABC):

    @abstractmethod
    def get_identity(self):
        pass
