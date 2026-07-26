import json
from pathlib import Path
from datetime import datetime

class AuditLogger:
    """Traçabilité centralisée et structurée de toutes les actions et décisions de l'agent."""
    def __init__(self, audit_dir="runtime/audit"):
        self.audit_dir = Path(audit_dir)
        self.audit_dir.mkdir(parents=True, exist_ok=True)
        self.tool_calls_file = self.audit_dir / "tool_calls.jsonl"
        self.security_file = self.audit_dir / "security_events.jsonl"
        self.decisions_file = self.audit_dir / "decisions.jsonl"

    def log_tool(self, request, result, duration: float = 0.0):
        record = {
            "time": datetime.now().isoformat(),
            "id": getattr(request, "request_id", "unknown"),
            "tool": request.name,
            "arguments": request.arguments,
            "success": result.success,
            "error": result.error if not result.success else None,
            "duration_sec": round(duration, 3)
        }
        self._append(self.tool_calls_file, record)

    def log_security(self, message: str, level: str = "WARNING"):
        record = {
            "time": datetime.now().isoformat(),
            "level": level,
            "message": message
        }
        self._append(self.security_file, record)

    def log_decision(self, step: str, details: dict):
        record = {
            "time": datetime.now().isoformat(),
            "step": step,
            "details": details
        }
        self._append(self.decisions_file, record)

    def _append(self, path: Path, data: dict):
        try:
            with open(path, "a", encoding="utf-8") as f:
                f.write(json.dumps(data, ensure_ascii=False) + "\n")
        except Exception:
            pass