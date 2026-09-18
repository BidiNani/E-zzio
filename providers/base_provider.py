from abc import ABC, abstractmethod
from typing import Any

from providers.provider_response import ProviderResponse


class BaseProvider(ABC):
    @abstractmethod
    async def generate(
        self, prompt: str, model: str | None = None, image_bytes: bytes | None = None, capability: str = "default"
    ) -> ProviderResponse:
        pass

    @abstractmethod
    def health(self) -> dict[str, Any]:
        pass

    @abstractmethod
    def capabilities(self) -> list:
        pass
