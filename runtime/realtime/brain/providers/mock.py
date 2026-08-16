import asyncio
from typing import AsyncGenerator
from .base import IBrainProvider
from ..contracts import BrainRequest, BrainResponseChunk
from runtime.realtime.voice.cancellation import CancellationToken

class MockProvider(IBrainProvider):
    def __init__(self, ttft_delay: float = 0.1, token_delay: float = 0.02):
        self.ttft_delay = ttft_delay
        self.token_delay = token_delay

    async def generate_stream(
        self, 
        request: BrainRequest, 
        cancellation_token: CancellationToken
    ) -> AsyncGenerator[BrainResponseChunk, None]:
        
        # Inférence TTFT simulation
        await asyncio.sleep(self.ttft_delay)
        
        sentence = "E-ZZIO real-time distributed cancellation pipeline is fully operational across voice and brain loops."
        words = sentence.split(" ")
        
        for i, word in enumerate(words):
            if cancellation_token.is_cancelled():
                yield BrainResponseChunk(
                    request_id=request.request_id,
                    chunk_text="",
                    is_final=True,
                    status="INTERRUPTED",
                    metadata={"interrupted_at_index": i, "total_tokens": len(words)}
                )
                return

            await asyncio.sleep(self.token_delay)
            is_final = (i == len(words) - 1)
            
            yield BrainResponseChunk(
                request_id=request.request_id,
                chunk_text=word + ("" if is_final else " "),
                is_final=is_final,
                status="COMPLETED" if is_final else "GENERATING"
            )
