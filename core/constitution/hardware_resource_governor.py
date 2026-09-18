"""E-ZZIO Core — Sovereign Hardware & Gaming Resource Governor (V10.0 Enterprise).

Enforces physical execution feasibility, hardware sovereignty, and anti-oversubscription.
Arbitrates between NOMINAL, PRESSURE, SATURATION, and GAMING_COEXISTENCE modes.
Provides deterministic resource verdicts: ALLOW, THROTTLE, QUEUE, DEFER, REJECT, EMERGENCY_DEGRADE.
"""

from __future__ import annotations

import logging
import sys
import threading
from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import Enum
from pathlib import Path
from typing import Any

import psutil

ROOT_DIR = Path(r"G:\AI\E-zzio")
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from core.cognition.decision_ledger import DecisionLedgerEngine

logger = logging.getLogger(__name__)


class ResourceVerdict(str, Enum):
    ALLOW = "ALLOW"
    THROTTLE = "THROTTLE"
    QUEUE = "QUEUE"
    DEFER = "DEFER"
    REJECT = "REJECT"
    EMERGENCY_DEGRADE = "EMERGENCY_DEGRADE"


class SystemPressureLevel(str, Enum):
    NOMINAL = "NOMINAL"
    PRESSURE = "PRESSURE"
    SATURATION = "SATURATION"
    GAMING_COEXISTENCE = "GAMING_COEXISTENCE"
    INCOHERENT_TELEMETRY = "INCOHERENT_TELEMETRY"


@dataclass
class ResourceDecision:
    decision_id: str
    task_id: str
    verdict: ResourceVerdict
    pressure_level: SystemPressureLevel
    allocated_threads: int
    allocated_ram_mb: int
    gpu_isolated: bool
    rationale: str
    telemetry_snapshot: dict[str, Any]
    timestamp_utc: str = field(default_factory=lambda: datetime.now(UTC).isoformat())


class HardwareResourceGovernor:
    GAMING_PROCESS_SIGNATURES = {
        "wow.exe", "wowclassic.exe", "battle.net.exe", "steam.exe",
        "discord.exe", "obs64.exe", "cyberpunk2077.exe", "eldenring.exe"
    }

    def __init__(self, root_dir: Path = ROOT_DIR):
        self.root_dir = root_dir
        self.max_threads_nominal = 16
        self.max_threads_pressure = 8
        self.max_threads_gaming = 4
        self.max_threads_saturation = 2

        self.simulated_telemetry: dict[str, Any] | None = None
        self.active_allocations: dict[str, int] = {}  # task_id -> allocated_ram_mb
        self._lock = threading.Lock()

        self.decision_engine = None
        try:
            self.decision_engine = DecisionLedgerEngine(root_dir=self.root_dir)
        except Exception:
            pass

    def detect_gaming_activity(self) -> bool:
        """Inspects process table for gaming or streaming binaries."""
        if self.simulated_telemetry and "gaming_override" in self.simulated_telemetry:
            return bool(self.simulated_telemetry["gaming_override"])

        try:
            for proc in psutil.process_iter(["name"]):
                p_name = proc.info.get("name")
                if p_name and p_name.lower() in self.GAMING_PROCESS_SIGNATURES:
                    return True
        except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
            pass
        return False

    def get_system_telemetry(self) -> dict[str, Any]:
        """Captures instantaneous real or simulated telemetry snapshot."""
        if self.simulated_telemetry:
            return self.simulated_telemetry

        try:
            cpu_pct = psutil.cpu_percent(interval=0.05)
            ram = psutil.virtual_memory()
            is_gaming = self.detect_gaming_activity()
            profile_name = "GAMING_COEXISTENCE_MODE" if is_gaming else "NORMAL_OPERATION_MODE"
            recommended_threads = self.max_threads_gaming if is_gaming else self.max_threads_nominal

            return {
                "profile": profile_name,
                "gaming_detected": is_gaming,
                "cpu_percent": cpu_pct,
                "cpu_system_usage_percent": cpu_pct,
                "ram_available_mb": int(ram.available / (1024**2)),
                "ram_available_gb": round(ram.available / (1024**3), 2),
                "ram_total_mb": int(ram.total / (1024**2)),
                "ram_percent": ram.percent,
                "ram_usage_percent": ram.percent,
                "allocated_ezzio_threads": recommended_threads,
                "gpu_policy": "ISOLATED_GAMING_ONLY (GTX 1650 Untouched)",
            }
        except Exception as e:
            logger.warning(f"[HARDWARE GOVERNOR] Telemetry probe failed: {e}")
            return {
                "profile": "FAIL_CLOSED_PROTECTION_MODE",
                "gaming_detected": True,  # Fail-closed safe default
                "cpu_percent": None,
                "cpu_system_usage_percent": None,
                "ram_available_mb": None,
                "ram_available_gb": None,
                "ram_total_mb": None,
                "ram_percent": None,
                "ram_usage_percent": None,
                "allocated_ezzio_threads": 1,
                "gpu_policy": "ISOLATED_GAMING_ONLY (GTX 1650 Untouched)",
                "error": str(e),
            }

    def evaluate_pressure_level(self, telemetry: dict[str, Any]) -> SystemPressureLevel:
        """Determines the active physical pressure tier."""
        if telemetry.get("cpu_percent") is None or telemetry.get("ram_available_mb") is None:
            return SystemPressureLevel.INCOHERENT_TELEMETRY

        if telemetry.get("gaming_detected", False):
            return SystemPressureLevel.GAMING_COEXISTENCE

        ram_mb = telemetry["ram_available_mb"]
        cpu_pct = telemetry["cpu_percent"]

        if ram_mb < 2048 or cpu_pct >= 85.0:
            return SystemPressureLevel.SATURATION
        elif ram_mb < 4096 or cpu_pct >= 70.0:
            return SystemPressureLevel.PRESSURE
        else:
            return SystemPressureLevel.NOMINAL

    def evaluate_task_request(
        self,
        task_id: str,
        requested_provider: str,
        requested_threads: int = 1,
        requested_ram_mb: int = 512,
        priority: str = "normal",  # "low", "normal", "high", "critical"
        override_flags: dict[str, Any] | None = None,
    ) -> ResourceDecision:
        """
        Sovereign arbitration of physical resource allocations.
        Guarantees no external provider can force or oversubscribe resources.
        """
        with self._lock:
            # 1. Anti-Bypass Check: Reject illegal override attempts
            if override_flags and override_flags.get("override_governor"):
                logger.error(f"[HARDWARE GOVERNOR] Unauthorized bypass flag rejected for {task_id}.")
                return self._build_and_record_decision(
                    task_id=task_id,
                    verdict=ResourceVerdict.REJECT,
                    pressure=SystemPressureLevel.NOMINAL,
                    threads=0,
                    ram_mb=0,
                    gpu_iso=True,
                    rationale="SECURITY VETO: Unauthorized override_governor flag rejected.",
                    telemetry={},
                )

            telemetry = self.get_system_telemetry()
            pressure = self.evaluate_pressure_level(telemetry)

            # Fail-Closed handling for incoherent telemetry
            if pressure == SystemPressureLevel.INCOHERENT_TELEMETRY:
                return self._build_and_record_decision(
                    task_id=task_id,
                    verdict=ResourceVerdict.THROTTLE,
                    pressure=pressure,
                    threads=1,
                    ram_mb=min(requested_ram_mb, 256),
                    gpu_iso=True,
                    rationale="FAIL-CLOSED: Incoherent telemetry; default safe throttled profile enforced.",
                    telemetry=telemetry,
                )

            ram_available = telemetry.get("ram_available_mb", 1024)

            # 2. Emergency Degrade Check (Active RAM starvation < 1024 MB)
            if ram_available < 1024 and priority != "critical":
                return self._build_and_record_decision(
                    task_id=task_id,
                    verdict=ResourceVerdict.EMERGENCY_DEGRADE,
                    pressure=pressure,
                    threads=1,
                    ram_mb=128,
                    gpu_iso=True,
                    rationale=f"EMERGENCY DEGRADE: Critical RAM starvation ({ram_available} MB available < 1024 MB). Non-critical task degraded.",
                    telemetry=telemetry,
                )

            # 3. Oversubscription Rejection Check (Physical Hard Barrier)
            current_allocated_ram = sum(self.active_allocations.values())
            if (current_allocated_ram + requested_ram_mb) > ram_available or requested_ram_mb > ram_available:
                return self._build_and_record_decision(
                    task_id=task_id,
                    verdict=ResourceVerdict.REJECT,
                    pressure=pressure,
                    threads=0,
                    ram_mb=0,
                    gpu_iso=True,
                    rationale=f"REJECTED: Oversubscription request ({requested_ram_mb} MB + {current_allocated_ram} MB active) exceeds available physical RAM ({ram_available} MB).",
                    telemetry=telemetry,
                )

            # 3. Gaming Mode Coexistence
            if pressure == SystemPressureLevel.GAMING_COEXISTENCE:
                if requested_provider in {"local_ollama", "agent_antigravity"} and requested_ram_mb > 4096:
                    return self._build_and_record_decision(
                        task_id=task_id,
                        verdict=ResourceVerdict.DEFER,
                        pressure=pressure,
                        threads=0,
                        ram_mb=0,
                        gpu_iso=True,
                        rationale="DEFERRED: Heavy local model deferred during Gaming Coexistence mode to protect GPU & Frame Times.",
                        telemetry=telemetry,
                    )
                allocated_t = min(requested_threads, self.max_threads_gaming)
                allocated_r = min(requested_ram_mb, 2048)
                self.active_allocations[task_id] = allocated_r
                return self._build_and_record_decision(
                    task_id=task_id,
                    verdict=ResourceVerdict.THROTTLE,
                    pressure=pressure,
                    threads=allocated_t,
                    ram_mb=allocated_r,
                    gpu_iso=True,
                    rationale=f"THROTTLED: Gaming active; capped to {allocated_t} threads & {allocated_r} MB RAM with GPU isolation.",
                    telemetry=telemetry,
                )

            # 4. Saturation Tier
            if pressure == SystemPressureLevel.SATURATION:
                if priority in {"low", "normal"}:
                    return self._build_and_record_decision(
                        task_id=task_id,
                        verdict=ResourceVerdict.QUEUE,
                        pressure=pressure,
                        threads=0,
                        ram_mb=0,
                        gpu_iso=False,
                        rationale="QUEUED: System saturated (CPU >= 85% or RAM < 2GB). Normal priority task queued.",
                        telemetry=telemetry,
                    )
                allocated_t = min(requested_threads, self.max_threads_saturation)
                allocated_r = min(requested_ram_mb, 1024)
                self.active_allocations[task_id] = allocated_r
                return self._build_and_record_decision(
                    task_id=task_id,
                    verdict=ResourceVerdict.THROTTLE,
                    pressure=pressure,
                    threads=allocated_t,
                    ram_mb=allocated_r,
                    gpu_iso=False,
                    rationale="THROTTLED: System saturated; allowed only minimal execution budget.",
                    telemetry=telemetry,
                )

            # 5. Oversubscription Rejection Check (Under Pressure or Nominal)
            current_allocated_ram = sum(self.active_allocations.values())
            if (current_allocated_ram + requested_ram_mb) > ram_available:
                return self._build_and_record_decision(
                    task_id=task_id,
                    verdict=ResourceVerdict.REJECT,
                    pressure=pressure,
                    threads=0,
                    ram_mb=0,
                    gpu_iso=True,
                    rationale=f"REJECTED: Oversubscription request ({requested_ram_mb} MB + {current_allocated_ram} MB active) exceeds available physical RAM ({ram_available} MB).",
                    telemetry=telemetry,
                )

            # 6. Pressure Tier
            if pressure == SystemPressureLevel.PRESSURE:
                allocated_t = min(requested_threads, self.max_threads_pressure)
                allocated_r = min(requested_ram_mb, 4096)
                self.active_allocations[task_id] = allocated_r
                return self._build_and_record_decision(
                    task_id=task_id,
                    verdict=ResourceVerdict.THROTTLE,
                    pressure=pressure,
                    threads=allocated_t,
                    ram_mb=allocated_r,
                    gpu_iso=False,
                    rationale=f"THROTTLED: System under pressure; allocated {allocated_t} threads & {allocated_r} MB RAM.",
                    telemetry=telemetry,
                )

            # 7. Nominal Tier
            allocated_t = min(requested_threads, self.max_threads_nominal)
            self.active_allocations[task_id] = requested_ram_mb
            return self._build_and_record_decision(
                task_id=task_id,
                verdict=ResourceVerdict.ALLOW,
                pressure=pressure,
                threads=allocated_t,
                ram_mb=requested_ram_mb,
                gpu_iso=False,
                rationale="ALLOW: Nominal system state; full execution parameters approved.",
                telemetry=telemetry,
            )

    def release_task_resources(self, task_id: str) -> None:
        """Releases allocated RAM tracking when task finishes."""
        with self._lock:
            self.active_allocations.pop(task_id, None)

    def _build_and_record_decision(
        self,
        task_id: str,
        verdict: ResourceVerdict,
        pressure: SystemPressureLevel,
        threads: int,
        ram_mb: int,
        gpu_iso: bool,
        rationale: str,
        telemetry: dict[str, Any],
    ) -> ResourceDecision:
        dec_id = f"HRD-{datetime.now(UTC).strftime('%Y%m%d')}-{task_id}"
        rec = ResourceDecision(
            decision_id=dec_id,
            task_id=task_id,
            verdict=verdict,
            pressure_level=pressure,
            allocated_threads=threads,
            allocated_ram_mb=ram_mb,
            gpu_isolated=gpu_iso,
            rationale=rationale,
            telemetry_snapshot=telemetry,
        )

        if self.decision_engine:
            try:
                self.decision_engine.record_decision(
                    subsystem="HardwareGovernor",
                    decision_type=f"RESOURCE_{verdict.value}",
                    context={"task_id": task_id, "pressure_level": pressure.value, "allocated_threads": threads, "allocated_ram_mb": ram_mb},
                    action_payload={"gpu_isolated": gpu_iso, "verdict": verdict.value},
                    rationale=rationale,
                )
            except Exception as le:
                logger.warning(f"[HARDWARE GOVERNOR] Ledger recording warning: {le}")

        return rec
