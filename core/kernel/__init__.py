"""E-ZZIO Core Kernel package."""
# ruff: noqa: F401 — re-exports API publique
from core.kernel.native_harness import (
    HarnessState,
    InvalidTransitionError,
    NativeHarness,
    TaskSession,
    TerminationReason,
)
