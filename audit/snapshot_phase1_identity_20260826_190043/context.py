from core.identity.canonical_identity import CanonicalIdentity
import json
from pathlib import Path
from typing import Dict, Any, Optional


class EzzioContextInjector:
    def __init__(self, root_dir: Optional[Path] = None):
        self.root_dir = root_dir or Path(r"G:\AI\E-zzio")
        self.health_file = self.root_dir / "runtime" / "state" / "backend" / "health.json"
        self.integrity_file = self.root_dir / "runtime" / "audit" / "integrity" / "sha256_baseline_v1.json"

    def _get_system_state(self) -> Dict[str, Any]:
        state = {"status": "UNKNOWN", "workers": "8/8"}
        if self.health_file.exists():
            try:
                data = json.loads(self.health_file.read_text(encoding="utf-8"))
                state["status"] = data.get("status", "UNKNOWN")
                state["pid"] = data.get("pid", "N/A")
            except Exception:
                pass
        return state

    def build_system_prompt(self, base_system_prompt: Optional[str] = None) -> str:
        canonical = CanonicalIdentity().build_system_prompt()
        base_system_prompt = base_system_prompt or canonical
        state = self._get_system_state()
        runtime_context = (
            f"[CONTEXTE ROUTEUR KERNEL]\n"
            f"- Status: {state.get('status')}\n"
            f"- PID: {state.get('pid')}"
        )
        if base_system_prompt:
            return f"{base_system_prompt}\n\n{runtime_context}"
        return runtime_context
