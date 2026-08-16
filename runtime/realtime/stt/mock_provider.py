import asyncio
import time
import numpy as np
from .provider import ISttProvider, SttResult

class MockSttProvider(ISttProvider):
    def __init__(self, canned_text: str = "Bonjour E-ZZIO, le système est opérationnel.", latency_ms: float = 30.0, fail_next: bool = False):
        self.canned_text = canned_text
        self.latency_ms = latency_ms
        self.fail_next = fail_next
        self.call_count = 0

    async def transcribe(self, audio: np.ndarray, sample_rate: int) -> SttResult:
        t0 = time.perf_counter()
        self.call_count += 1
        await asyncio.sleep(self.latency_ms / 1000.0)
        if self.fail_next:
            self.fail_next = False
            raise RuntimeError("Mock STT intentional failure for isolation testing.")
        t1 = time.perf_counter()
        duration_s = len(audio) / float(sample_rate)
        return SttResult(
            text=self.canned_text,
            confidence=0.99,
            duration_s=duration_s,
            latencies={"stt_exec_ms": (t1 - t0) * 1000.0},
            provenance={"sample_rate": sample_rate, "samples": len(audio), "call_index": self.call_count}
        )
