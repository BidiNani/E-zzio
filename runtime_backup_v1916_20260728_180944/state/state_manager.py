import json
from pathlib import Path
from datetime import datetime

class StateManager:
    def __init__(self, state_dir="runtime/state"):
        self.state_dir = Path(state_dir)
        self.state_dir.mkdir(parents=True, exist_ok=True)
        self.state_file = self.state_dir / "state.json"
        self.load()

    def load(self):
        if self.state_file.exists():
            try:
                self.data = json.loads(self.state_file.read_text(encoding="utf-8"))
            except Exception:
                self._init_default()
        else:
            self._init_default()

    def _init_default(self):
        self.data = {
            "mode": "development",
            "project": "E-zzio",
            "current_goal": "Runtime Kernel & State Management",
            "last_file": "runtime/kernel.py",
            "last_action": "bootstrap_state_manager",
            "confidence": 0.95,
            "updated_at": datetime.now().isoformat()
        }
        self.save()

    def save(self):
        self.data["updated_at"] = datetime.now().isoformat()
        self.state_file.write_text(json.dumps(self.data, ensure_ascii=False, indent=2), encoding="utf-8")

    def update(self, **kwargs):
        for key, value in kwargs.items():
            self.data[key] = value
        self.save()

    def get_state_prompt_block(self):
        return f"""
[ÉTAT SYSTÈME ACTUEL & INTENTION]
- Mode : {self.data.get('mode')}
- Projet : {self.data.get('project')}
- Objectif en cours : {self.data.get('current_goal')}
- Dernier fichier manipulé : {self.data.get('last_file')}
- Dernière action : {self.data.get('last_action')}
"""