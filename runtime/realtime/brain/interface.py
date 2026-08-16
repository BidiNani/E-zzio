from typing import AsyncGenerator
from .contracts import BrainRequest, BrainResponseChunk

class IBrainWorker:
    """Contrat d'interface strict isolant la boucle vocale de la boucle d'intelligence."""
    async def ask_stream(self, request: BrainRequest) -> AsyncGenerator[BrainResponseChunk, None]:
        raise NotImplementedError("Les workers d'intelligence doivent implémenter ask_stream()")
