import asyncio
import time
from typing import Any


class KeyScheduler:
    def __init__(self, keys: list[str]):
        self.keys = keys
        self.states: list[dict[str, Any]] = [{"status": "ACTIVE", "blocked_until": 0.0} for _ in keys]
        self.current_index = 0
        self._lock = None

    async def get_next_key(self) -> tuple[int | None, str | None]:
        if not self.keys:
            return None, None

        if self._lock is None:
            self._lock = asyncio.Lock()

        try:
            await asyncio.wait_for(self._lock.acquire(), timeout=5.0)
        except TimeoutError:
            raise TimeoutError("KEY_POOL_LOCK_TIMEOUT")

        try:
            start_index = self.current_index
            now = time.time()

            while True:
                state = self.states[self.current_index]

                if state["status"] == "BLOCKED" and now > state["blocked_until"]:
                    state["status"] = "ACTIVE"
                    state["blocked_until"] = 0.0

                if state["status"] == "ACTIVE":
                    idx = self.current_index
                    key = self.keys[idx]
                    self.current_index = (self.current_index + 1) % len(self.keys)
                    return idx, key

                self.current_index = (self.current_index + 1) % len(self.keys)

                if self.current_index == start_index:
                    raise RuntimeError("KEY_POOL_EXHAUSTED_429")
        finally:
            self._lock.release()

    def mark_exhausted(self, index: int, ttl_seconds: float = 3600.0):
        if 0 <= index < len(self.states):
            self.states[index]["status"] = "BLOCKED"
            self.states[index]["blocked_until"] = time.time() + ttl_seconds

    def mark_invalid(self, index: int):
        if 0 <= index < len(self.states):
            self.states[index]["status"] = "INVALID"
            self.states[index]["blocked_until"] = float("inf")

    def get_active_count(self) -> int:
        now = time.time()
        return sum(1 for s in self.states if s["status"] == "ACTIVE" or (s["status"] == "BLOCKED" and now > s["blocked_until"]))
