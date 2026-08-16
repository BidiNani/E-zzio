import json
import time
from pathlib import Path
from datetime import datetime, timezone
from typing import Optional
from .schemas import ModelResponse

class RouterTelemetry:
    def __init__(self, audit_dir: Optional[Path] = None):
        self.audit_dir = audit_dir or Path("G:/AI/E-zzio/runtime/audit")
        self.audit_dir.mkdir(parents=True, exist_ok=True)
        self.log_file = self.audit_dir / "model_usage.jsonl"

    def log_usage(self, agent_id: str, request_task: str, response: ModelResponse) -> None:
        entry = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "agent": agent_id,
            "task": request_task,
            "model": response.model_used,
            "provider": response.provider_used,
            "tokens_in": response.tokens_evaluated,
            "tokens_out": response.tokens_generated,
            "latency_ms": round(response.latency_ms, 2),
            "fallback": response.fallback_applied
        }
        try:
            with open(self.log_file, "a", encoding="utf-8") as f:
                f.write(json.dumps(entry) + "\n")
        except Exception:
            pass
