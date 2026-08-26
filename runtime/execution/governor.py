from __future__ import annotations
import threading


class ResourceGovernor:
    """Garant des limites matérielles (CPU, RAM, Timeouts, Workers parallèles)."""

    def __init__(self, hard_limits: dict):
        self.limits = hard_limits
        self._active_workers = 0
        self._lock = threading.RLock()

    def allocate(self, requested_budget: dict) -> tuple[bool, str, dict]:
        """Vérifie et alloue des ressources selon la Constitution."""
        with self._lock:
            if self._active_workers >= self.limits.get("max_parallel_workers", 8):
                return False, "QUOTA_EXCEEDED: Max parallel workers reached.", {}

            cpu = min(requested_budget.get("cpu", 2), self.limits.get("max_cpu_threads_per_worker", 8))
            ram = min(requested_budget.get("ram_mb", 512), self.limits.get("max_ram_mb_per_sandbox", 4096))
            timeout = min(requested_budget.get("timeout", 10), self.limits.get("max_execution_time_sec", 300))

            allocated = {"cpu": cpu, "ram_mb": ram, "timeout": timeout}
            self._active_workers += 1
            return True, "APPROVED", allocated

    def release(self):
        with self._lock:
            if self._active_workers > 0:
                self._active_workers -= 1
