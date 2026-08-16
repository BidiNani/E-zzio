"""
E-ZZIO V9.5.0 — Experience Ledger Manager
Enregistre passivement les succès, les échecs et les patterns comportementaux.
"""
import json
from pathlib import Path
from datetime import datetime, timezone

ROOT_DIR = Path(r"G:\AI\E-zzio")
LEDGER_DIR = ROOT_DIR / "runtime" / "experience" / "ledger"
PATTERNS_DIR = ROOT_DIR / "runtime" / "experience" / "patterns"

class ExperienceLedger:
    def __init__(self):
        LEDGER_DIR.mkdir(parents=True, exist_ok=True)
        PATTERNS_DIR.mkdir(parents=True, exist_ok=True)

    def log_success(self, workflow_id: str, capabilities: list, duration_ms: float, memory_peak_mb: float, confidence: float) -> dict:
        entry = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "workflow_id": workflow_id,
            "capabilities": capabilities,
            "duration_ms": duration_ms,
            "memory_peak_mb": memory_peak_mb,
            "status": "SUCCESS",
            "confidence_after_execution": confidence
        }
        path = LEDGER_DIR / "workflow_success.jsonl"
        with open(path, "a", encoding="utf-8") as f:
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")
        return entry

    def log_failure(self, workflow_id: str, capability: str, failure_type: str, resolution: str) -> dict:
        entry = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "workflow_id": workflow_id,
            "capability": capability,
            "failure": failure_type,
            "resolution": resolution,
            "status": "FAILURE"
        }
        path = LEDGER_DIR / "workflow_failure.jsonl"
        with open(path, "a", encoding="utf-8") as f:
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")
        return entry

    def save_pattern(self, pattern_name: str, pattern_data: dict):
        path = PATTERNS_DIR / "learned_patterns.json"
        data = {}
        if path.exists():
            try:
                data = json.loads(path.read_text(encoding="utf-8"))
            except Exception:
                data = {}
        
        data[pattern_name] = {
            "updated_utc": datetime.now(timezone.utc).isoformat(),
            "data": pattern_data
        }
        path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
