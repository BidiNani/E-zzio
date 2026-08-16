import asyncio
from typing import AsyncGenerator
from .contracts import BrainRequest, BrainResponseChunk
from .interface import IBrainWorker

class MockBrainWorker(IBrainWorker):
    def __init__(self, ttft_delay: float = 0.3, token_delay: float = 0.05):
        self.ttft_delay = ttft_delay
        self.token_delay = token_delay

    async def ask_stream(self, request: BrainRequest) -> AsyncGenerator[BrainResponseChunk, None]:
        # Simulation du Time To First Token (RAG + LLM Prompt processing)
        await asyncio.sleep(self.ttft_delay)
        
        simulated_response = f"Message reçu par le cerveau simulé. Contenu de la requête : {request.text}"
        words = simulated_response.split(" ")
        
        for i, word in enumerate(words):
            await asyncio.sleep(self.token_delay)
            is_final = (i == len(words) - 1)
            # On ajoute un espace pour reconstituer la phrase
            yield BrainResponseChunk(
                request_id=request.request_id,
                chunk_text=word + ("" if is_final else " "),
                is_final=is_final
            )
