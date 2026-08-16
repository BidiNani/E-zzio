from __future__ import annotations
from enum import Enum, auto
import threading
import time

class RuntimePhase(Enum):
    PRE_BOOT = auto()
    CONSTITUTION_CHECK = auto()
    SECURING_VAULT = auto()
    READY = auto()
    SUSPENDED = auto()
    PANIC = auto()
    HALTED = auto()

class EzzioRuntimeState:
    _ALLOWED_TRANSITIONS = {
        RuntimePhase.PRE_BOOT: {RuntimePhase.CONSTITUTION_CHECK, RuntimePhase.PANIC},
        RuntimePhase.CONSTITUTION_CHECK: {RuntimePhase.SECURING_VAULT, RuntimePhase.PANIC},
        RuntimePhase.SECURING_VAULT: {RuntimePhase.READY, RuntimePhase.PANIC},
        RuntimePhase.READY: {RuntimePhase.SUSPENDED, RuntimePhase.PANIC, RuntimePhase.HALTED},
        RuntimePhase.SUSPENDED: {RuntimePhase.READY, RuntimePhase.PANIC, RuntimePhase.HALTED},
        RuntimePhase.PANIC: {RuntimePhase.HALTED},
        RuntimePhase.HALTED: set(),
    }

    def __init__(self):
        self._lock = threading.RLock()
        self._phase = RuntimePhase.PRE_BOOT
        self._boot_time: float | None = None
        self._panic_reason: str | None = None

    def transition(self, new_phase: RuntimePhase, reason: str | None = None) -> None:
        with self._lock:
            if new_phase not in self._ALLOWED_TRANSITIONS[self._phase]:
                raise RuntimeError(f"Transition interdite : {self._phase.name} -> {new_phase.name}")

            self._phase = new_phase

            if new_phase == RuntimePhase.READY:
                if self._boot_time is None:
                    self._boot_time = time.time()

            if new_phase == RuntimePhase.PANIC:
                self._panic_reason = reason or "Unknown kernel panic"

    @property
    def current_phase(self) -> RuntimePhase:
        with self._lock:
            return self._phase

    @property
    def boot_time(self) -> float | None:
        with self._lock:
            return self._boot_time

    @property
    def panic_reason(self) -> str | None:
        with self._lock:
            return self._panic_reason

kernel_state = EzzioRuntimeState()