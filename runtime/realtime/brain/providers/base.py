from typing import AsyncGenerator
from ..contracts import BrainRequest, BrainResponseChunk
from runtime.realtime.voice.cancellation import CancellationToken

class IBrainProvider:
    """Contrat d'interface strict pour tout fournisseur d'intelligence (Local ou API)."""
    async def generate_stream(
        self, 
        request: BrainRequest, 
        cancellation_token: CancellationToken
    ) -> AsyncGenerator[BrainResponseChunk, None]:
        raise NotImplementedError("Les providers doivent implémenter generate_stream()")
