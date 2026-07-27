from typing import Dict, Any, List

class SessionManager:
    """Gestionnaire de contexte utilisateur en mémoire pour isoler les historiques de conversation."""
    def __init__(self):
        self.active_sessions: Dict[str, Dict[str, Any]] = {}

    def get_or_create(self, user_id: str) -> Dict[str, Any]:
        if user_id not in self.active_sessions:
            self.active_sessions[user_id] = {
                "user_id": user_id,
                "message_count": 0,
                "history": [],
                "memory_scope": "private"
            }
        return self.active_sessions[user_id]

    def clear_session(self, user_id: str):
        if user_id in self.active_sessions:
            del self.active_sessions[user_id]
