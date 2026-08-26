"""E-ZZIO secure multi-key pool.

Secrets are loaded from environment variables at runtime and are never
serialized, represented, or emitted in forensic status.

Supported naming convention:
    GEMINI_API_KEY
    GEMINI_API_KEY_2
    ...
    GROQ_API_KEY
    GROQ_API_KEY_2
    ...
    OPENROUTER_API_KEY
    OPENROUTER_API_KEY_2
    ...

The manager deliberately does not know the actual secret value outside
the in-memory KeySlot object.
"""

from __future__ import annotations

import os
import time
from dataclasses import dataclass, field
from enum import StrEnum
from threading import Lock
from typing import Any


class KeyState(StrEnum):
    READY = "READY"
    IN_USE = "IN_USE"
    COOLDOWN = "COOLDOWN"
    QUOTA_EXHAUSTED = "QUOTA_EXHAUSTED"
    INVALID = "INVALID"


@dataclass(slots=True)
class KeySlot:
    slot_id: str
    provider: str
    env_var_name: str
    secret_value: str = field(repr=False)

    state: KeyState = KeyState.READY
    cooldown_until: float = 0.0
    daily_requests: int = 0
    consecutive_errors: int = 0
    total_successes: int = 0
    total_failures: int = 0
    last_used: float = 0.0
    created_at: float = field(default_factory=time.time)

    def available(self, now: float | None = None) -> bool:
        now = time.time() if now is None else now

        if self.state == KeyState.READY:
            return True

        if self.state == KeyState.COOLDOWN and now >= self.cooldown_until:
            self.state = KeyState.READY
            self.consecutive_errors = 0
            return True

        return False


class KeyPoolManager:
    """Thread-safe provider key scheduler."""

    PREFIXES: dict[str, tuple[str, ...]] = {
        "gemini": ("GEMINI_API_KEY",),
        "groq": ("GROQ_API_KEY",),
        "openrouter": ("OPENROUTER_API_KEY",),
    }

    def __init__(
        self,
        *,
        cooldown_seconds: float = 60.0,
        max_consecutive_errors: int = 3,
    ) -> None:
        self.cooldown_seconds = cooldown_seconds
        self.max_consecutive_errors = max_consecutive_errors

        self._slots: dict[str, list[KeySlot]] = {}
        self._lock = Lock()

        self._load_from_environment()

    def _load_from_environment(self) -> None:
        for provider, roots in self.PREFIXES.items():
            slots: list[KeySlot] = []

            for root in roots:
                names = [root]

                for index in range(2, 101):
                    names.append(f"{root}_{index}")

                for index, env_name in enumerate(names, start=1):
                    value = os.environ.get(env_name, "").strip()

                    if not value:
                        continue

                    slots.append(
                        KeySlot(
                            slot_id=f"{provider.upper()}_KEY_{index:02d}",
                            provider=provider,
                            env_var_name=env_name,
                            secret_value=value,
                        )
                    )

            self._slots[provider] = slots

    def providers(self) -> list[str]:
        return sorted(self._slots)

    def available_slots(self, provider: str) -> list[KeySlot]:
        provider = provider.lower()

        with self._lock:
            slots = self._slots.get(provider, [])

            available = [
                slot for slot in slots
                if slot.available()
            ]

            available.sort(
                key=lambda slot: (
                    slot.last_used,
                    slot.daily_requests,
                    slot.consecutive_errors,
                )
            )

            return available

    def acquire(self, provider: str) -> KeySlot | None:
        candidates = self.available_slots(provider)

        if not candidates:
            return None

        with self._lock:
            slot = candidates[0]
            slot.state = KeyState.IN_USE
            slot.last_used = time.time()
            return slot

    def mark_success(self, slot: KeySlot) -> None:
        with self._lock:
            slot.state = KeyState.READY
            slot.daily_requests += 1
            slot.total_successes += 1
            slot.consecutive_errors = 0
            slot.last_used = time.time()

    def mark_rate_limited(
        self,
        slot: KeySlot,
        cooldown_seconds: float | None = None,
    ) -> None:
        with self._lock:
            slot.total_failures += 1
            slot.consecutive_errors += 1
            slot.state = KeyState.COOLDOWN
            slot.cooldown_until = (
                time.time()
                + (
                    self.cooldown_seconds
                    if cooldown_seconds is None
                    else cooldown_seconds
                )
            )

    def mark_quota_exhausted(
        self,
        slot: KeySlot,
        cooldown_seconds: float = 3600.0,
    ) -> None:
        with self._lock:
            slot.total_failures += 1
            slot.consecutive_errors += 1
            slot.state = KeyState.QUOTA_EXHAUSTED
            slot.cooldown_until = time.time() + cooldown_seconds

    def mark_invalid(self, slot: KeySlot) -> None:
        with self._lock:
            slot.total_failures += 1
            slot.state = KeyState.INVALID

    def mark_failure(self, slot: KeySlot) -> None:
        with self._lock:
            slot.total_failures += 1
            slot.consecutive_errors += 1

            if slot.consecutive_errors >= self.max_consecutive_errors:
                slot.state = KeyState.COOLDOWN
                slot.cooldown_until = (
                    time.time() + self.cooldown_seconds
                )
            else:
                slot.state = KeyState.READY

    def forensic_status(self) -> list[dict[str, Any]]:
        with self._lock:
            result: list[dict[str, Any]] = []

            for provider, slots in sorted(self._slots.items()):
                for slot in slots:
                    result.append(
                        {
                            "slot_id": slot.slot_id,
                            "provider": provider,
                            "env_var": slot.env_var_name,
                            "state": slot.state.value,
                            "daily_requests": slot.daily_requests,
                            "total_successes": slot.total_successes,
                            "total_failures": slot.total_failures,
                            "consecutive_errors": slot.consecutive_errors,
                            "available": slot.available(),
                        }
                    )

            return result