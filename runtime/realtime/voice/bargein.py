import asyncio
from typing import Dict, Optional
from dataclasses import dataclass, field
from time import time
from .cancellation import CancellationToken

@dataclass
class BargeInEvent:
    request_id: str
    source: str = "USER"
    reason: str = "NEW_INPUT"
    timestamp: float = field(default_factory=time)

class BargeInController:
    def __init__(self):
        self._tokens: Dict[str, CancellationToken] = {}
        self._events: Dict[str, BargeInEvent] = {}
        self._lock = asyncio.Lock()

    async def register(self, request_id: str) -> CancellationToken:
        async with self._lock:
            token = CancellationToken()
            self._tokens[request_id] = token
            return token

    async def interrupt(self, request_id: str, source: str = "USER", reason: str = "NEW_INPUT"):
        async with self._lock:
            token = self._tokens.get(request_id)
            if token:
                token.cancel()
                self._events[request_id] = BargeInEvent(
                    request_id=request_id,
                    source=source,
                    reason=reason
                )

    async def is_interrupted(self, request_id: str) -> bool:
        async with self._lock:
            token = self._tokens.get(request_id)
            return token.is_cancelled() if token else False

    async def get_event(self, request_id: str) -> Optional[BargeInEvent]:
        async with self._lock:
            return self._events.get(request_id)

    async def unregister(self, request_id: str):
        async with self._lock:
            self._tokens.pop(request_id, None)
            self._events.pop(request_id, None)
