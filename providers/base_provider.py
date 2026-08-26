from abc import ABC, abstractmethod
from typing import Optional, Dict, Any
from providers.provider_response import ProviderResponse


class BaseProvider(ABC):
    @abstractmethod
    async def generate(
        self, prompt: str, model: Optional[str] = None, image_bytes: Optional[bytes] = None, capability: str = "default"
    ) -> ProviderResponse:
        pass

    @abstractmethod
    def health(self) -> Dict[str, Any]:
        pass

    @abstractmethod
    def capabilities(self) -> list:
        pass
