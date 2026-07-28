import json
from pathlib import Path
from datetime import datetime
from runtime.core.message import Message

class WorkingMemory:
    def __init__(self, path="runtime/memory/working_memory.json"):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.session_id = f"session_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        self.messages = []
        self.load()

    def load(self):
        if self.path.exists():
            try:
                data = json.loads(self.path.read_text(encoding="utf-8"))
                self.session_id = data.get("session_id", self.session_id)
                
                # Auto-migration et validation stricte via Message.from_dict()
                raw_messages = data.get("messages", [])
                self.messages = [
                    Message.from_dict(m).to_dict()
                    for m in raw_messages
                ]
            except Exception:
                self.messages = []

    def save(self):
        payload = {
            "session_id": self.session_id,
            "updated_at": datetime.now().isoformat(),
            "messages": self.messages
        }
        self.path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    def add(self, role: str, content: str, source: str = "terminal"):
        """Ajoute un message via le contrat unifié Message."""
        msg = Message(role=role, content=content, source=source)
        self.messages.append(msg.to_dict())
        # Fenêtre glissante de 20 messages
        self.messages = self.messages[-20:]
        self.save()

    def recent(self, limit=6):
        """Encapsule la récupération des derniers messages pour le ContextBuilder."""
        return self.messages[-limit:]

    def clear(self):
        self.messages = []
        self.save()