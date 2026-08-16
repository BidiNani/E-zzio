"""
E-ZZIO V9.7 — Personal Knowledge Manager
Gère l'apprentissage explicite (Observation -> Pattern -> Confirmation -> Mémoire Permanente).
"""
import json
from pathlib import Path
from datetime import datetime, timezone

ROOT_DIR = Path(r"G:\AI\E-zzio")
KNOWLEDGE_DIR = ROOT_DIR / "runtime" / "knowledge"

class PersonalKnowledgeManager:
    def __init__(self):
        self.pref_dir = KNOWLEDGE_DIR / "preferences"
        self.val_dir = KNOWLEDGE_DIR / "validation"
        self.proj_dir = KNOWLEDGE_DIR / "projects"
        
        self.pending_file = self.val_dir / "pending_confirmations.json"
        self.confirmed_file = self.pref_dir / "confirmed_preferences.json"
        
        self._ensure_files()

    def _ensure_files(self):
        if not self.pending_file.exists():
            self.pending_file.write_text("{}", encoding="utf-8")
        if not self.confirmed_file.exists():
            self.confirmed_file.write_text("{}", encoding="utf-8")

    def propose_preference_pattern(self, pattern_id: str, description: str, proposed_value: dict) -> dict:
        """Étape 1 & 2 : Pattern détecté -> Proposition en attente de validation."""
        pending = json.loads(self.pending_file.read_text(encoding="utf-8"))
        entry = {
            "timestamp_utc": datetime.now(timezone.utc).isoformat(),
            "description": description,
            "proposed_value": proposed_value,
            "status": "PENDING_USER_CONFIRMATION"
        }
        pending[pattern_id] = entry
        self.pending_file.write_text(json.dumps(pending, indent=2, ensure_ascii=False), encoding="utf-8")
        return entry

    def confirm_preference(self, pattern_id: str) -> dict:
        """Étape 3 & 4 : Validation humaine -> Enregistrement permanent."""
        pending = json.loads(self.pending_file.read_text(encoding="utf-8"))
        if pattern_id not in pending:
            return {"status": "NOT_FOUND", "reason": f"Aucun pattern en attente pour {pattern_id}"}

        entry = pending.pop(pattern_id)
        entry["status"] = "CONFIRMED"
        entry["confirmed_at_utc"] = datetime.now(timezone.utc).isoformat()

        confirmed = json.loads(self.confirmed_file.read_text(encoding="utf-8"))
        confirmed[pattern_id] = entry

        self.pending_file.write_text(json.dumps(pending, indent=2, ensure_ascii=False), encoding="utf-8")
        self.confirmed_file.write_text(json.dumps(confirmed, indent=2, ensure_ascii=False), encoding="utf-8")
        return entry

    def get_confirmed_preferences(self) -> dict:
        return json.loads(self.confirmed_file.read_text(encoding="utf-8"))
