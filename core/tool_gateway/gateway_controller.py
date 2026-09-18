"""
E-ZZIO V7.39 — Tool Gateway Controller
Passe-plat sécurisé pour toutes les interactions externes. Intercepte les appels,
évalue les risques via le manifeste, et gère les autorisations.
"""

import json
import uuid
from datetime import UTC, datetime
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent.parent
MANIFEST_FILE = ROOT_DIR / "runtime" / "tools" / "manifest.json"
ACTION_LOG_FILE = ROOT_DIR / "runtime" / "tools" / "action_ledger.jsonl"


class ToolGatewayController:
    def __init__(self):
        self.manifest = self._load_manifest()
        ACTION_LOG_FILE.parent.mkdir(parents=True, exist_ok=True)

    def _load_manifest(self) -> dict:
        if MANIFEST_FILE.exists():
            return json.loads(MANIFEST_FILE.read_text(encoding="utf-8"))
        return {"tools": {}}

    def request_action(self, tool_name: str, payload: dict, intent: str) -> dict:
        action_id = f"ACT-{uuid.uuid4().hex[:8].upper()}"
        tool_config = self.manifest.get("tools", {}).get(tool_name)

        if not tool_config:
            return self._log_action(action_id, tool_name, "REJECTED_UNKNOWN_TOOL", "CRITICAL")

        risk = tool_config.get("risk_level", "CRITICAL")

        # Logique V7.43 (Secure Action Layer embarquée)
        if risk == "LOW":
            status = "APPROVED_AUTO"
        elif risk == "MEDIUM":
            status = "APPROVED_WITH_AUDIT"
        else:  # HIGH or CRITICAL
            status = "WAITING_APPROVAL"

        return self._log_action(action_id, tool_name, status, risk, payload, intent)

    def _log_action(self, action_id: str, tool_name: str, status: str, risk: str, payload: dict = None, intent: str = "") -> dict:
        record = {
            "action_id": action_id,
            "timestamp": datetime.now(UTC).isoformat(),
            "tool": tool_name,
            "intent": intent,
            "risk_level": risk,
            "status": status,
            "payload_hash": hash(str(payload)) if payload else None,
        }

        with open(ACTION_LOG_FILE, "a", encoding="utf-8") as f:
            f.write(json.dumps(record, ensure_ascii=False) + "\n")

        return record


tool_gateway = ToolGatewayController()
