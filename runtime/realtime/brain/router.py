from typing import Dict, AsyncGenerator
from .contracts import BrainRequest, BrainResponseChunk
from .providers.base import IBrainProvider
from .providers.mock import MockProvider
from runtime.realtime.voice.cancellation import CancellationToken

class BrainProviderRouter:
    def __init__(self, default_provider: str = "mock"):
        self.providers: Dict[str, IBrainProvider] = {
            "mock": MockProvider()
        }
        self.default_provider_name = default_provider

    def register_provider(self, name: str, provider: IBrainProvider):
        self.providers[name] = provider

    async def ask_stream(
        self, 
        request: BrainRequest, 
        cancellation_token: CancellationToken
    ) -> AsyncGenerator[BrainResponseChunk, None]:
        
        target = request.provider_override or self.default_provider_name
        provider = self.providers.get(target)
        
        if not provider:
            # Fallback automatique sur le mock si le provider demandé est indisponible
            provider = self.providers[self.default_provider_name]

        async for chunk in provider.generate_stream(request, cancellation_token):
            yield chunk
