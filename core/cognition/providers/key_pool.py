"""E-ZZIO Core — Sovereign Provider Key Pool & Quota Manager (Phase 6.2).

Provides an 8-state, thread-safe, rate-limit aware round-robin key rotation scheduler
for Cloud Providers (Gemini, Groq, etc.) ensuring zero raw secret leakage in logs or audit traces.
"""

from __future__ import annotations

import logging
import threading
import time
from dataclasses import dataclass
from enum import Enum
from typing import Any

logger = logging.getLogger(__name__)


class KeyStatus(Enum):
    AVAILABLE = "AVAILABLE"
    RATE_LIMITED = "RATE_LIMITED"
    QUOTA_EXHAUSTED = "QUOTA_EXHAUSTED"
    AUTH_FAILED = "AUTH_FAILED"
    TEMPORARILY_UNAVAILABLE = "TEMPORARILY_UNAVAILABLE"
    REVOKED = "REVOKED"
    DEGRADED = "DEGRADED"
    UNKNOWN = "UNKNOWN"


@dataclass
class KeySlot:
    slot_id: str
    key_secret: str
    masked_key: str
    status: KeyStatus = KeyStatus.AVAILABLE
    blocked_until: float = 0.0
    failure_count: int = 0
    success_count: int = 0
    last_used_timestamp: float = 0.0
    last_error_code: int | None = None

    @classmethod
    def create(cls, slot_id: str, raw_key: str) -> KeySlot:
        clean = raw_key.strip()
        masked = f"...{clean[-4:]}" if len(clean) >= 4 else "***"
        return cls(slot_id=slot_id, key_secret=clean, masked_key=masked)


class SovereignKeyPool:
    def __init__(self, provider_name: str, raw_keys: list[str]):
        self.provider_name = provider_name
        self.slots: list[KeySlot] = [
            KeySlot.create(slot_id=f"{provider_name}-key-{i+1:02d}", raw_key=k)
            for i, k in enumerate(raw_keys)
            if k and k.strip()
        ]
        self.current_index = 0
        self._lock = threading.Lock()

    def get_next_key(self) -> tuple[int | None, str | None, str | None]:
        """
        Thread-safe retrieval of next available key.
        Returns (slot_index, raw_secret, masked_key) or (None, None, None) if all exhausted.
        """
        with self._lock:
            if not self.slots:
                return None, None, None

            start_idx = self.current_index
            now = time.time()

            for _ in range(len(self.slots)):
                slot = self.slots[self.current_index]

                # Check cooldown expiry
                if slot.status in {KeyStatus.RATE_LIMITED, KeyStatus.QUOTA_EXHAUSTED, KeyStatus.TEMPORARILY_UNAVAILABLE}:
                    if now >= slot.blocked_until:
                        slot.status = KeyStatus.AVAILABLE
                        slot.blocked_until = 0.0

                if slot.status == KeyStatus.AVAILABLE:
                    idx = self.current_index
                    slot.last_used_timestamp = now
                    self.current_index = (self.current_index + 1) % len(self.slots)
                    return idx, slot.key_secret, slot.masked_key

                self.current_index = (self.current_index + 1) % len(self.slots)

            return None, None, None

    def mark_rate_limited(self, index: int, ttl_seconds: float = 60.0, error_code: int = 429) -> None:
        with self._lock:
            if 0 <= index < len(self.slots):
                slot = self.slots[index]
                slot.status = KeyStatus.RATE_LIMITED
                slot.blocked_until = time.time() + ttl_seconds
                slot.failure_count += 1
                slot.last_error_code = error_code
                logger.warning(f"[KEY POOL] {self.provider_name} slot {slot.slot_id} ({slot.masked_key}) rate-limited for {ttl_seconds}s.")

    def mark_quota_exhausted(self, index: int, ttl_seconds: float = 3600.0, error_code: int = 429) -> None:
        with self._lock:
            if 0 <= index < len(self.slots):
                slot = self.slots[index]
                slot.status = KeyStatus.QUOTA_EXHAUSTED
                slot.blocked_until = time.time() + ttl_seconds
                slot.failure_count += 1
                slot.last_error_code = error_code
                logger.warning(f"[KEY POOL] {self.provider_name} slot {slot.slot_id} ({slot.masked_key}) quota exhausted for {ttl_seconds}s.")

    def mark_auth_failed(self, index: int, error_code: int = 401) -> None:
        with self._lock:
            if 0 <= index < len(self.slots):
                slot = self.slots[index]
                slot.status = KeyStatus.AUTH_FAILED
                slot.blocked_until = float("inf")
                slot.failure_count += 1
                slot.last_error_code = error_code
                logger.error(f"[KEY POOL] {self.provider_name} slot {slot.slot_id} ({slot.masked_key}) auth failed permanently.")

    def mark_success(self, index: int) -> None:
        with self._lock:
            if 0 <= index < len(self.slots):
                slot = self.slots[index]
                slot.success_count += 1
                slot.status = KeyStatus.AVAILABLE

    def export_state(self) -> dict[str, Any]:
        """Exports pool state without leaking raw secrets for persistent recovery."""
        with self._lock:
            return {
                "provider_name": self.provider_name,
                "current_index": self.current_index,
                "slots_state": [
                    {
                        "slot_id": s.slot_id,
                        "masked_key": s.masked_key,
                        "status": s.status.value,
                        "blocked_until": s.blocked_until,
                        "failure_count": s.failure_count,
                        "success_count": s.success_count,
                        "last_error_code": s.last_error_code,
                    }
                    for s in self.slots
                ]
            }

    def restore_state(self, state_dict: dict[str, Any]) -> None:
        """Restores cooldowns and status after service restart."""
        with self._lock:
            self.current_index = state_dict.get("current_index", 0)
            slots_map = {s["slot_id"]: s for s in state_dict.get("slots_state", [])}
            for slot in self.slots:
                if slot.slot_id in slots_map:
                    st = slots_map[slot.slot_id]
                    try:
                        slot.status = KeyStatus(st.get("status", "AVAILABLE"))
                    except Exception:
                        slot.status = KeyStatus.AVAILABLE
                    slot.blocked_until = st.get("blocked_until", 0.0)
                    slot.failure_count = st.get("failure_count", 0)
                    slot.success_count = st.get("success_count", 0)
                    slot.last_error_code = st.get("last_error_code")

    def sanitize_exception(self, exc: Exception) -> str:
        """Strips any raw secret string from exception text or stacktrace."""
        raw_msg = str(exc)
        for s in self.slots:
            if s.key_secret and s.key_secret in raw_msg:
                raw_msg = raw_msg.replace(s.key_secret, s.masked_key)
        return raw_msg
