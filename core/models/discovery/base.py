"""Provider discovery base classes."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any


class ProviderDiscovery(ABC):

    provider: str

    @abstractmethod
    async def discover(
        self,
        api_key: str,
    ) -> list[dict[str, Any]]:
        """Discover currently available models."""
        raise NotImplementedError
