from datetime import datetime

class Message:
    """
    Contrat de message unifié pour toutes les sources d'E-zzio 
    (Terminal, Discord, API Web, Voix, etc.).
    """
    def __init__(self, role: str, content: str, source: str = "terminal"):
        self.role = role
        self.content = content
        self.timestamp = datetime.now().isoformat()
        self.source = source

    def to_dict(self) -> dict:
        return {
            "role": self.role,
            "content": self.content,
            "timestamp": self.timestamp,
            "source": self.source
        }

    @classmethod
    def from_dict(cls, data: dict):
        msg = cls(
            role=data.get("role", "user"),
            content=data.get("content", ""),
            source=data.get("source", "unknown")
        )
        msg.timestamp = data.get("timestamp", datetime.now().isoformat())
        return msg

    def __repr__(self):
        return f"<Message {self.source}/{self.role}: {self.content[:50]}>"