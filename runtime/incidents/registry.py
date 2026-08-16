from __future__ import annotations
from enum import Enum
import json
import uuid
from pathlib import Path
from datetime import datetime
from typing import Any, Dict

class IncidentRegistry:
    """Registre persistant des incidents et anomalies du Runtime au format JSONL."""
    
    def __init__(self, log_dir: Path = Path("runtime/incidents")):
        self.log_dir = log_dir
        self.log_dir.mkdir(parents=True, exist_ok=True)
        self.log_file = self.log_dir / "incidents.jsonl"

    def report(self, incident_type: str, actor: str, severity: str, details: Dict[str, Any]) -> str:
        """Enregistre un incident de manière immuable avec un ID unique."""
        inc_id = f"INC-{datetime.now().strftime('%Y%m%d')}-{uuid.uuid4().hex[:6].upper()}"
        record = {
            "id": inc_id,
            "timestamp": datetime.now().isoformat(),
            "type": incident_type,
            "actor": actor,
            "severity": severity,
            "details": details
        }
        with open(self.log_file, "a", encoding="utf-8") as f:
            f.write(json.dumps(record) + "\n")
        return inc_id

    def query(self, actor: str = None) -> list[dict]:
        """Interroge l'historique des incidents (filtrable par acteur)."""
        if not self.log_file.exists():
            return []
        incidents = []
        for line in self.log_file.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            try:
                data = json.loads(line)
                if actor is None or data.get("actor") == actor:
                    incidents.append(data)
            except Exception:
                pass
        return incidents