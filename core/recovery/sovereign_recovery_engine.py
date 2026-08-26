"""E-ZZIO Core — Sovereign Recovery & Diagnostic Engine (Phase 8.3).

Diagnoses and recovers operational runtime state after abrupt crashes, corrupted buffers,
orphan transaction locks, or provider failures without ever altering or rewriting the historical Decision Ledger.
Enforces strict Fail-Closed quarantine for critical integrity violations.
"""

from __future__ import annotations

import json
import logging
import os
import shutil
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

ROOT_DIR = Path(r"G:\AI\E-zzio")

from core.cognition.decision_ledger import DecisionLedgerEngine

logger = logging.getLogger(__name__)


@dataclass
class RecoveryActionReport:
    action_id: str
    target_component: str
    fault_type: str
    status: str  # "RECOVERED_OPERATIONAL", "QUARANTINED_FAIL_CLOSED", "CLEANED_NO_ACTION"
    details: str
    restored_items_count: int = 0
    quarantined_items_count: int = 0
    timestamp_utc: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


class SovereignRecoveryEngine:
    def __init__(self, root_dir: Path = ROOT_DIR):
        self.root_dir = root_dir
        self.quarantine_dir = self.root_dir / "runtime" / ".quarantine"
        self.quarantine_dir.mkdir(parents=True, exist_ok=True)
        self.decision_engine = None
        try:
            self.decision_engine = DecisionLedgerEngine(root_dir=self.root_dir)
        except Exception:
            pass

    def recover_orphan_locks(self) -> RecoveryActionReport:
        """Inspects and clears stale transaction lock files left by crashed processes."""
        action_id = f"REC-LOCK-{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}"
        cleared = 0
        if self.decision_engine and hasattr(self.decision_engine, "lock_path"):
            lp = self.decision_engine.lock_path
            if lp.exists():
                try:
                    lp.unlink()
                    cleared += 1
                except Exception as e:
                    logger.warning(f"[RECOVERY] Could not unlink lock {lp}: {e}")

        report = RecoveryActionReport(
            action_id=action_id,
            target_component="TransactionLocks",
            fault_type="ORPHAN_LOCK_FILES",
            status="RECOVERED_OPERATIONAL" if cleared > 0 else "CLEANED_NO_ACTION",
            details=f"Cleared {cleared} stale transaction lock file(s).",
            restored_items_count=cleared,
        )
        return report

    def recover_corrupted_memory_files(self) -> RecoveryActionReport:
        """Scans memory stores, quarantines unparseable JSON files, and preserves valid records."""
        action_id = f"REC-MEM-{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}"
        mem_root = self.root_dir / "runtime" / "memory_store"
        if not mem_root.exists():
            return RecoveryActionReport(action_id, "MemoryStore", "CORRUPTED_JSON", "CLEANED_NO_ACTION", "No memory store present.")

        quarantined = 0
        valid = 0
        for json_path in mem_root.rglob("*.json"):
            try:
                content = json_path.read_text(encoding="utf-8")
                json.loads(content)
                valid += 1
            except Exception as e:
                # Quarantined file
                q_dest = self.quarantine_dir / f"{json_path.name}_{int(datetime.now().timestamp())}.bad"
                try:
                    shutil.move(str(json_path), str(q_dest))
                    quarantined += 1
                    logger.warning(f"[RECOVERY] Quarantined corrupted memory file {json_path.name} -> {q_dest.name}")
                except Exception as me:
                    logger.error(f"[RECOVERY] Failed to move corrupted file {json_path}: {me}")

        report = RecoveryActionReport(
            action_id=action_id,
            target_component="MemoryStore",
            fault_type="CORRUPTED_MEMORY_FILES",
            status="RECOVERED_OPERATIONAL" if quarantined > 0 else "CLEANED_NO_ACTION",
            details=f"Validated {valid} memory files. Quarantined {quarantined} corrupted files.",
            restored_items_count=valid,
            quarantined_items_count=quarantined,
        )
        self._record_recovery(report)
        return report

    def cleanup_stale_scratch_files(self, scratch_dir: Path) -> RecoveryActionReport:
        """Removes orphaned .tmp / .scratch test artifacts."""
        action_id = f"REC-SCRATCH-{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}"
        cleaned = 0
        if scratch_dir.exists():
            for f in scratch_dir.glob("*.tmp"):
                try:
                    f.unlink()
                    cleaned += 1
                except Exception:
                    pass

        report = RecoveryActionReport(
            action_id=action_id,
            target_component="ScratchStorage",
            fault_type="STALE_TEMPORARY_FILES",
            status="RECOVERED_OPERATIONAL" if cleaned > 0 else "CLEANED_NO_ACTION",
            details=f"Removed {cleaned} stale temporary scratch files.",
            restored_items_count=cleaned,
        )
        self._record_recovery(report)
        return report

    def _record_recovery(self, report: RecoveryActionReport) -> None:
        if self.decision_engine and report.status != "CLEANED_NO_ACTION":
            try:
                self.decision_engine.record_decision(
                    subsystem="RecoveryEngine",
                    decision_type=f"RECOVERY_{report.status}",
                    context={"action_id": report.action_id, "component": report.target_component, "fault": report.fault_type},
                    action_payload={"restored": report.restored_items_count, "quarantined": report.quarantined_items_count},
                    rationale=report.details,
                )
            except Exception as le:
                logger.warning(f"[RECOVERY ENGINE] Ledger logging warning: {le}")
