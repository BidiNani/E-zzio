import json
import sys
from pathlib import Path
from datetime import datetime

class AuditLogger:
    def __init__(self, audit_dir=None):
        if audit_dir is None:
            audit_dir = Path(__file__).resolve().parents[1] / "audit"
        self.audit_dir = Path(audit_dir)
        self.audit_dir.mkdir(parents=True, exist_ok=True)
        self.tool_calls_file = self.audit_dir / "tool_calls.jsonl"
        self.security_file = self.audit_dir / "security_events.jsonl"
        self.agent_actions_file = self.audit_dir / "agent_actions.jsonl"

    def log_tool(self, request, result, duration: float, metadata: dict = None):
        record = {
            "time": datetime.now().isoformat(),
            "id": getattr(request, "request_id", "unknown"),
            "tool": request.name,
            "arguments": request.arguments,
            "success": result.success,
            "error": result.error if not result.success else None,
            "duration_sec": round(duration, 3),
            "os_metrics": metadata or {}
        }
        self._append(self.tool_calls_file, record)

    def log_security(self, message: str, level: str = "WARNING"):
        self._append(self.security_file, {"time": datetime.now().isoformat(), "level": level, "message": message})

    def log_agent_action(self, session_id: str, step: int, tool_name: str, success: bool, duration: float):
        self._append(self.agent_actions_file, {"session": session_id, "step": step, "tool": tool_name, "success": success, "duration_sec": round(duration, 3), "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")})

    def _append(self, path: Path, data: dict):
        try:
            with open(path, "a", encoding="utf-8") as f:
                f.write(json.dumps(data, ensure_ascii=False) + "\n")
        except Exception as e:
            print(f"[CRITICAL AUDIT ERROR] {e}", file=sys.stderr)