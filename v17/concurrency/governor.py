import threading
from typing import Dict, Any

SAFE_MAX_CONCURRENCY = 20

class ResourceGovernor:
    def __init__(self, max_concurrent: int = SAFE_MAX_CONCURRENCY):
        self.max_concurrent = max_concurrent
        self._active_count = 0
        self._lock = threading.Lock()

    def acquire_slot(self) -> bool:
        with self._lock:
            if self._active_count < self.max_concurrent:
                self._active_count += 1
                return True
            return False

    def release_slot(self):
        with self._lock:
            if self._active_count > 0:
                self._active_count -= 1

    @property
    def active_tasks(self) -> int:
        with self._lock:
            return self._active_count

    @property
    def capacity(self) -> int:
        return self.max_concurrent

resource_governor = ResourceGovernor()
