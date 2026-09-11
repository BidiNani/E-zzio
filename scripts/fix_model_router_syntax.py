from pathlib import Path

ROOT = Path(r"G:\AI\E-zzio")
ROUTER_DIR = ROOT / "runtime" / "model_router"

# 1. Correction health.py
health_code = """import requests
import os
from pathlib import Path
from typing import Dict, Any

class ModelHealthChecker:
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.ollama_host = config.get("ollama_host", "http://127.0.0.1:11434")

    def check_ollama(self) -> bool:
        try:
            res = requests.get(f"{self.ollama_host}/api/tags", timeout=2)
            return res.status_code == 200
        except Exception:
            return False

    def check_gemini(self) -> bool:
        return bool(os.getenv("GEMINI_API_KEY"))

    def check_gguf_path(self, relative_path: str) -> bool:
        full_path = Path("G:/AI/E-zzio") / relative_path
        return full_path.exists()
"""

# 2. Correction telemetry.py
telemetry_code = """import json
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
                f.write(json.dumps(entry) + "\\n")
        except Exception:
            pass
"""

(ROUTER_DIR / "health.py").write_text(health_code, encoding="utf-8")
(ROUTER_DIR / "telemetry.py").write_text(telemetry_code, encoding="utf-8")

print("[OK] Fichiers health.py et telemetry.py corrigés.")
